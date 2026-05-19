"""DeepSeek provider — primary chat provider per ADR-018.

Talks to https://api.deepseek.com directly via httpx (OpenAI-compatible API
shape, but we avoid the openai-python dependency for narrower attack surface
and Wave 0 dependency hygiene). Embeddings unsupported — DeepSeek has no
embeddings endpoint as of 2026-Q2.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from src.llm_gateway.providers.base import LLMRequest, LLMResponse, LLMUsage

_logger = structlog.get_logger(__name__)


class DeepSeekProvider:
    """OpenAI-shaped JSON over httpx.AsyncClient."""

    name: str = "deepseek"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _body(req: LLMRequest, *, stream: bool) -> dict[str, Any]:
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
                f"{self._base_url}/v1/chat/completions",
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
                cached_input_tokens=int(usage_block.get("prompt_cache_hit_tokens", 0)),
            ),
            raw_provider_metadata={"provider": "deepseek", "model": req.model},
        )

    async def chat_stream(self, req: LLMRequest) -> AsyncIterator[LLMResponse]:
        """Yield ``LLMResponse`` chunks from SSE stream.

        Note: Async generators wrapped in `async def` cannot use early-return
        without exhausting the stream — we just await chunks and yield.
        """
        async with (
            self._client() as client,
            client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
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
                    import json

                    chunk = json.loads(payload)
                except ValueError:
                    _logger.warning("deepseek.stream.malformed_chunk", raw=payload)
                    continue
                delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                yield LLMResponse(
                    content=delta.get("content", "") or "",
                    finish_reason=(chunk.get("choices") or [{}])[0].get("finish_reason") or "stop",
                    raw_provider_metadata={"provider": "deepseek"},
                )

    async def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError(
            "DeepSeek has no embeddings endpoint — use yandexgpt or openai (BYOK)."
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self._base_url)
        except httpx.HTTPError as exc:
            _logger.info("deepseek.health.unreachable", error=str(exc))
            return False
        # DeepSeek root often returns 404 / 405 but if the server responded,
        # the upstream is reachable for our purposes.
        return resp.status_code < 500
