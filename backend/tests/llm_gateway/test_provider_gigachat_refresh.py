"""AC-W1-10: GigaChat OAuth refresh-after-expiry + concurrent-refresh token lock.

These drive the REAL ``GigaChatProvider._ensure_token`` (unlike the
``_PatchedGigaChatProvider`` suites, which override it) by monkeypatching the
module's ``httpx.AsyncClient`` to inject a MockTransport.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.gigachat import GigaChatProvider

_OAUTH_HOST = "ngw.devices.sberbank.ru"


def _install_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    original = httpx.AsyncClient

    def patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("src.llm_gateway.providers.gigachat.httpx.AsyncClient", patched)


@pytest.mark.asyncio
async def test_ensure_token_refreshes_after_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale (expired) token forces a fresh OAuth round-trip before chat, and
    the chat call carries the newly-minted bearer token."""
    oauth_calls = 0
    chat_auth_header: str | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal oauth_calls, chat_auth_header
        if request.url.host == _OAUTH_HOST:
            oauth_calls += 1
            return httpx.Response(200, json={"access_token": "fresh-token", "expires_at": 0})
        if "/chat/completions" in request.url.path:
            chat_auth_header = request.headers.get("authorization")
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )
        return httpx.Response(404, json={"error": f"unhandled {request.url}"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    provider = GigaChatProvider(auth_key="k", verify_ssl=False)  # gitleaks:allow
    # Force an EXPIRED token so the fast-path is skipped and a refresh runs.
    provider._token = "stale-token"
    provider._token_expires_at = time.time() - 10

    resp = await provider.chat(
        LLMRequest(model="GigaChat-Pro", messages=[{"role": "user", "content": "hi"}])
    )

    assert resp.content == "ok"
    assert oauth_calls == 1  # the refresh round-trip happened
    assert chat_auth_header == "Bearer fresh-token"  # chat used the refreshed token


@pytest.mark.asyncio
async def test_concurrent_ensure_token_does_single_oauth_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The asyncio.Lock + double-check collapses a concurrent refresh storm into
    one OAuth round-trip (no duplicate refresh / token clobber)."""
    oauth_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal oauth_calls
        if request.url.host == _OAUTH_HOST:
            oauth_calls += 1
            return httpx.Response(
                200,
                json={"access_token": f"token-{oauth_calls}", "expires_at": 0},
            )
        return httpx.Response(404)

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    provider = GigaChatProvider(auth_key="k", verify_ssl=False)  # gitleaks:allow

    tokens = await asyncio.gather(*(provider._ensure_token() for _ in range(8)))

    assert oauth_calls == 1  # only the first waiter refreshed
    assert set(tokens) == {"token-1"}  # everyone got the same freshly-minted token
