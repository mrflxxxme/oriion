"""Unit: HttpxTransport — real streaming/cap/error-mapping via httpx.MockTransport.

Drives the REAL transport (no live network) so the body-size cap + typed-error
mapping are covered.
"""

from __future__ import annotations

import httpx
import pytest
from src.mcp.tools.connectors.base import HttpxTransport, redact_secrets
from src.mcp.tools.connectors.exceptions import ConnectorError

# Obviously-fake, too-short-to-match-gitleaks Telegram bot token.
_TOKEN = "123456:AA-secret"


@pytest.mark.asyncio
async def test_returns_body_and_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("a") == "1"
        return httpx.Response(200, json={"ok": True})

    tr = HttpxTransport(transport=httpx.MockTransport(handler))
    resp = await tr.request("GET", "https://api.test/x", params={"a": 1})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_http_error_status_maps_to_connector_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    tr = HttpxTransport(transport=httpx.MockTransport(handler))
    with pytest.raises(ConnectorError, match="http error: 404"):
        await tr.request("GET", "https://api.test/x")


@pytest.mark.asyncio
async def test_body_cap_aborts_oversized_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 4096)

    tr = HttpxTransport(transport=httpx.MockTransport(handler), max_body_bytes=1024)
    with pytest.raises(ConnectorError, match="exceeded"):
        await tr.request("GET", "https://api.test/x")


@pytest.mark.asyncio
async def test_network_error_maps_to_connector_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    tr = HttpxTransport(transport=httpx.MockTransport(handler))
    with pytest.raises(ConnectorError, match="network error"):
        await tr.request("GET", "https://api.test/x")


@pytest.mark.asyncio
async def test_network_error_redacts_bot_token_in_url() -> None:
    # A RequestError whose str() echoes the token-bearing URL must be scrubbed.
    url = f"https://api.telegram.org/bot{_TOKEN}/getUpdates"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"failed to connect to {url}")

    tr = HttpxTransport(transport=httpx.MockTransport(handler))
    with pytest.raises(ConnectorError) as ei:
        await tr.request("GET", url)
    message = str(ei.value)
    assert _TOKEN not in message
    assert "/bot<redacted>/" in message


def test_redact_secrets_scrubs_all_credential_forms() -> None:
    assert redact_secrets(f"/bot{_TOKEN}/getUpdates") == "/bot<redacted>/getUpdates"
    assert "topsecret" not in redact_secrets("url?token=topsecret&x=1")
    assert redact_secrets("Authorization: OAuth mytok") == "Authorization: OAuth <redacted>"
    assert redact_secrets("Api-Key abc123") == "Api-Key <redacted>"
    # Clean text is unchanged.
    assert redact_secrets("just a normal error") == "just a normal error"
