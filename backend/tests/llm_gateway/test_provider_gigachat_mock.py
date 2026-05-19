"""Mocked GigaChat provider tests via httpx MockTransport — OAuth flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.gigachat import GigaChatProvider

_OAUTH_FIXTURE = Path(__file__).parent / "fixtures" / "gigachat_oauth_response.json"
_CHAT_FIXTURE = Path(__file__).parent / "fixtures" / "gigachat_chat_response.json"


class _PatchedGigaChatProvider(GigaChatProvider):
    def __init__(self, *, transport: httpx.MockTransport, **kwargs: Any) -> None:
        # verify_ssl=False so the test transport doesn't try to validate certs
        # against the fake server.
        super().__init__(
            auth_key="test-base64-auth-key",  # gitleaks:allow
            verify_ssl=False,
            **kwargs,
        )
        self._transport = transport

    async def _ensure_token(self) -> str:  # type: ignore[override]
        # Force the OAuth call through the mock transport.
        import time
        from uuid import uuid4

        async with httpx.AsyncClient(transport=self._transport) as client:
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
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + 1800
        return self._token

    async def _client(self) -> httpx.AsyncClient:  # type: ignore[override]
        token = await self._ensure_token()
        return httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )


@pytest.mark.asyncio
async def test_gigachat_oauth_then_chat() -> None:
    oauth = json.loads(_OAUTH_FIXTURE.read_text(encoding="utf-8"))
    chat = json.loads(_CHAT_FIXTURE.read_text(encoding="utf-8"))

    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        # OAuth endpoint
        if request.url.host == "ngw.devices.sberbank.ru":
            return httpx.Response(200, json=oauth)
        # Chat completion
        if "/chat/completions" in request.url.path:
            return httpx.Response(200, json=chat)
        return httpx.Response(404, json={"error": f"unhandled {request.url}"})

    provider = _PatchedGigaChatProvider(transport=httpx.MockTransport(handler))
    resp = await provider.chat(
        LLMRequest(
            model="GigaChat-Pro",
            messages=[{"role": "user", "content": "Привет"}],
        )
    )
    assert "Здравствуйте" in resp.content
    assert resp.usage.tokens_input == 14
    assert resp.usage.tokens_output == 11
    # OAuth followed by chat — two distinct requests recorded.
    assert len(seen_paths) >= 2


@pytest.mark.asyncio
async def test_gigachat_health_check_returns_false_on_oauth_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "OAuth down"})

    provider = _PatchedGigaChatProvider(transport=httpx.MockTransport(handler))
    assert await provider.health_check() is False
