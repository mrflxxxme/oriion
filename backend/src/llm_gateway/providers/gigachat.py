"""GigaChat (Sber) provider — OAuth2 token-refresh + chat completion.

OAuth flow:
    POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth
      Authorization: Basic <auth_key>
      RqUID: <uuid>
      scope=GIGACHAT_API_PERS
    -> {access_token, expires_at}

Chat:
    POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
import structlog

from src.llm_gateway.providers.base import LLMRequest, LLMResponse, LLMUsage

_logger = structlog.get_logger(__name__)


class GigaChatProvider:
    """Sber GigaChat with on-demand OAuth2 refresh."""

    name: str = "gigachat"

    def __init__(
        self,
        auth_key: str,
        *,
        scope: str = "GIGACHAT_API_PERS",
        base_url: str = "https://gigachat.devices.sberbank.ru/api/v1",
        oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        timeout_seconds: float = 30.0,
        verify_ssl: bool | str = True,
    ) -> None:
        self._auth_key = auth_key
        self._scope = scope
        self._base_url = base_url.rstrip("/")
        self._oauth_url = oauth_url
        self._timeout = timeout_seconds
        # bool → enable/disable verification; str → path to a CA bundle that
        # carries the Russian Trusted Root CA (httpx accepts a path for
        # `verify=`). httpx/certifi ignores the OS store, so the prod image
        # points this at /etc/ssl/certs/ca-certificates.crt (AC-W1-21).
        self._verify_ssl = verify_ssl
        self._token: str | None = None
        # Epoch seconds — refresh ~60s before expiry.
        self._token_expires_at: float = 0.0

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        async with httpx.AsyncClient(timeout=self._timeout, verify=self._verify_ssl) as client:
            resp = await client.post(
                self._oauth_url,
                headers={
                    "Authorization": f"Basic {self._auth_key}",
                    "RqUID": str(uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                data={"scope": self._scope},
            )
            resp.raise_for_status()
            payload = resp.json()
        token = payload.get("access_token")
        if not isinstance(token, str):
            raise RuntimeError("gigachat OAuth response missing access_token")
        # Yandex/Sber return `expires_at` as ms epoch. Tolerate seconds too.
        expires_at_raw = payload.get("expires_at") or 0
        expires_at = (
            float(expires_at_raw) / 1000 if expires_at_raw > 1e12 else float(expires_at_raw)
        )
        if expires_at <= time.time():
            # Fallback: 30 min if upstream omits it.
            expires_at = time.time() + 1800
        self._token = token
        self._token_expires_at = expires_at
        return token

    def _body(self, req: LLMRequest, *, stream: bool) -> dict[str, Any]:
        return {
            "model": req.model,
            "messages": req.messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": stream,
        }

    async def _client(self) -> httpx.AsyncClient:
        token = await self._ensure_token()
        return httpx.AsyncClient(
            timeout=self._timeout,
            verify=self._verify_ssl,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    async def chat(self, req: LLMRequest) -> LLMResponse:
        client = await self._client()
        async with client:
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
            usage=LLMUsage(
                tokens_input=int(usage_block.get("prompt_tokens", 0)),
                tokens_output=int(usage_block.get("completion_tokens", 0)),
            ),
            raw_provider_metadata={"provider": "gigachat", "model": req.model},
        )

    async def chat_stream(self, req: LLMRequest) -> AsyncIterator[LLMResponse]:
        client = await self._client()
        async with (
            client,
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
                    _logger.warning("gigachat.stream.malformed_chunk", raw=payload)
                    continue
                delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                yield LLMResponse(
                    content=delta.get("content", "") or "",
                    finish_reason=(chunk.get("choices") or [{}])[0].get("finish_reason") or "stop",
                    raw_provider_metadata={"provider": "gigachat"},
                )

    async def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError("GigaChat embeddings deferred — use yandexgpt or openai (BYOK).")

    async def health_check(self) -> bool:
        try:
            await self._ensure_token()
        except (httpx.HTTPError, RuntimeError) as exc:
            _logger.info("gigachat.health.unreachable", error=str(exc))
            return False
        return True
