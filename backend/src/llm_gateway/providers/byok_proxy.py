"""BYOK proxy — decrypt customer key on-demand, forward to OpenAI-shaped upstream.

Supports model routing like ``byok-openai/gpt-4o`` where:
    - provider_slug (left of slash, after `byok-`)  → 'openai'
    - upstream model (right of slash)               → 'gpt-4o'

The KMS decryption happens per-request — plaintext never cached. Wave 0 ties
to a single upstream contract (OpenAI-compatible JSON); Anthropic native API
is a separate provider in Wave 2+.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from src.llm_gateway.providers.base import LLMRequest, LLMResponse, LLMUsage

_logger = structlog.get_logger(__name__)


# Provider → upstream base URL (OpenAI-compatible). Anthropic gets a separate
# native provider Wave 2+; Wave 0 BYOK supports openai shape only.
_BYOK_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",  # OpenAI-compatible proxy (3rd-party)
}


def parse_byok_model(model: str) -> tuple[str, str]:
    """Parse ``byok-<provider>/<model>`` -> (provider_slug, upstream_model).

    Examples:
        "byok-openai/gpt-4o"       -> ("openai", "gpt-4o")
        "byok-anthropic/claude-3"  -> ("anthropic", "claude-3")

    Raises ValueError if the syntax is wrong.
    """
    if not model.startswith("byok-"):
        raise ValueError(f"not a BYOK model spec: {model!r}")
    rest = model.removeprefix("byok-")
    if "/" not in rest:
        raise ValueError(f"BYOK model must be 'byok-<provider>/<model>': {model!r}")
    provider, upstream = rest.split("/", 1)
    return provider, upstream


class BYOKProxyProvider:
    """OpenAI-shaped JSON forwarder bound to a customer key.

    Constructed per-request by the router (or service layer) after the
    customer key has been decrypted via KMSProvider. The proxy DOES NOT cache
    plaintext — once the LLMResponse is built, the instance should be dropped.
    """

    name: str = "byok"

    def __init__(
        self,
        plaintext_key: str,
        upstream_provider_slug: str,
        *,
        base_url_override: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._key = plaintext_key
        self._upstream_provider = upstream_provider_slug
        base_url = base_url_override or _BYOK_BASE_URLS.get(upstream_provider_slug)
        if base_url is None:
            raise ValueError(
                f"BYOK provider {upstream_provider_slug!r} not supported "
                "(supply base_url_override or add to _BYOK_BASE_URLS)."
            )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
        )

    def _body(self, req: LLMRequest, *, stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": req.model,
            "messages": req.messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": stream,
        }
        if req.tools:
            body["tools"] = req.tools
        return body

    async def chat(self, req: LLMRequest) -> LLMResponse:
        async with self._client() as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=self._body(req, stream=False),
            )
            resp.raise_for_status()
            payload = resp.json()
        choices = payload.get("choices") or []
        first = choices[0] if choices else {}
        message = first.get("message", {})
        usage_block = payload.get("usage", {})
        return LLMResponse(
            content=message.get("content", "") or "",
            finish_reason=first.get("finish_reason", "stop"),
            tool_calls=message.get("tool_calls"),
            usage=LLMUsage(
                tokens_input=int(usage_block.get("prompt_tokens", 0)),
                tokens_output=int(usage_block.get("completion_tokens", 0)),
            ),
            raw_provider_metadata={
                "provider": f"byok-{self._upstream_provider}",
                "model": req.model,
            },
        )

    async def chat_stream(self, req: LLMRequest) -> AsyncIterator[LLMResponse]:
        async with (
            self._client() as client,
            client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=self._body(req, stream=True),
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line.removeprefix("data: ").strip()
                if payload == "[DONE]":
                    return
                try:
                    chunk = json.loads(payload)
                except ValueError:
                    _logger.warning("byok.stream.malformed_chunk", raw=payload)
                    continue
                delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                yield LLMResponse(
                    content=delta.get("content", "") or "",
                    finish_reason=(chunk.get("choices") or [{}])[0].get("finish_reason") or "stop",
                    raw_provider_metadata={"provider": f"byok-{self._upstream_provider}"},
                )

    async def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        async with self._client() as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                json={"model": model, "input": texts},
            )
            resp.raise_for_status()
            payload = resp.json()
        data = payload.get("data") or []
        return [[float(x) for x in item.get("embedding", [])] for item in data]

    async def health_check(self) -> bool:
        # Hitting `/models` validates auth + reachability.
        try:
            async with self._client() as client:
                resp = await client.get(f"{self._base_url}/models")
        except httpx.HTTPError as exc:
            _logger.info("byok.health.unreachable", error=str(exc))
            return False
        return resp.status_code < 500
