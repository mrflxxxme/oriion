"""F-P5-4 partial: GigaChat chat_stream SSE coverage.

Phase 00.5b Commit 7. GigaChat requires OAuth2 token refresh before each
HTTP call — the MockTransport handler intercepts both endpoints:

    * POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth → access_token
    * POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions → SSE

Streaming format matches OpenAI: `data: {...}` chunks terminated by
`data: [DONE]`.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.gigachat import GigaChatProvider


class _PatchedGigaChatProvider(GigaChatProvider):
    """Override client builders to inject MockTransport for BOTH the OAuth
    and chat endpoints (they live under different host URLs)."""

    def __init__(self, *, transport: httpx.MockTransport, **kwargs: Any) -> None:
        super().__init__(auth_key="test-basic-auth", **kwargs)
        self._transport = transport

    async def _ensure_token(self) -> str:  # type: ignore[override]
        # Force a refresh via mocked OAuth endpoint instead of going to the
        # real Sber NGW host. Otherwise httpx tries to connect to the
        # production URL even with MockTransport on the chat client.
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            resp = await client.post(
                self._oauth_url,
                headers={
                    "Authorization": f"Basic {self._auth_key}",
                    "RqUID": "test-rquid",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                data={"scope": self._scope},
            )
            resp.raise_for_status()
            payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = float(payload.get("expires_at", time.time() + 1800))
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


def _sse_body(chunks: list[dict]) -> bytes:
    lines: list[str] = []
    for chunk in chunks:
        lines.append(f"data: {json.dumps(chunk, ensure_ascii=False)}")
    lines.append("data: [DONE]")
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.mark.asyncio
async def test_gigachat_chat_stream_parses_sse_chunks() -> None:
    """Two-call handler: OAuth → token; then chat completion → SSE chunks."""
    chunks = [
        {"choices": [{"delta": {"content": "Здравствуй"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "!"}, "finish_reason": "stop"}]},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "expires_at": int((time.time() + 1800) * 1000),
                },
            )
        # Chat completion endpoint.
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(200, content=_sse_body(chunks))

    provider = _PatchedGigaChatProvider(transport=httpx.MockTransport(handler))
    received: list[str] = []
    finish: str | None = None
    async for resp in provider.chat_stream(
        LLMRequest(
            model="GigaChat-Pro",
            messages=[{"role": "user", "content": "Привет"}],
        )
    ):
        received.append(resp.content)
        finish = resp.finish_reason

    assert received == ["Здравствуй", "!"]
    assert finish == "stop"


@pytest.mark.asyncio
async def test_gigachat_chat_stream_refreshes_token_when_missing() -> None:
    """First _ensure_token call fetches a token; subsequent stream uses it."""
    token_calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth" in str(request.url):
            token_calls["n"] += 1
            return httpx.Response(
                200,
                json={
                    "access_token": f"token-{token_calls['n']}",
                    "expires_at": int((time.time() + 1800) * 1000),
                },
            )
        return httpx.Response(
            200,
            content=_sse_body(
                [{"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}]
            ),
        )

    provider = _PatchedGigaChatProvider(transport=httpx.MockTransport(handler))
    received = [
        r.content
        async for r in provider.chat_stream(
            LLMRequest(model="GigaChat-Pro", messages=[{"role": "user", "content": "x"}])
        )
    ]
    assert received == ["ok"]
    assert token_calls["n"] == 1, "OAuth should be called exactly once for fresh provider"
