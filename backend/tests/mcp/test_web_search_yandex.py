"""Unit: WebSearchTool — Yandex Search fallback + error paths."""

from __future__ import annotations

import httpx
import pytest
from src.mcp.exceptions import ToolRateLimitExceeded, WebSearchError
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.mcp.tools.web_search import WebSearchTool

YANDEX_JSON_PAYLOAD = {
    "results": [
        {"title": "Я-1", "url": "https://example.test/y1", "snippet": "snippet 1"},
        {"title": "Я-2", "url": "https://example.test/y2", "snippet": "snippet 2"},
    ],
}


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    transport: httpx.MockTransport,
) -> None:
    original = httpx.AsyncClient

    def patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("src.mcp.tools.web_search.httpx.AsyncClient", patched)


@pytest.mark.asyncio
async def test_yandex_search_used_when_brave_unset(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No Brave key + Yandex key set → Yandex path runs."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=YANDEX_JSON_PAYLOAD)

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="test-yandex")
    results = await tool.search("привет", agent_id="agent-1", max_results=2)
    assert len(results) == 2
    assert results[0].url == "https://example.test/y1"
    assert "yandex.ru" in str(captured["url"])


@pytest.mark.asyncio
async def test_yandex_xml_response_returns_empty_wave0(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yandex returns XML body; Wave 0 doesn't parse it → returns []."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<?xml version='1.0'?><response/>",
            headers={"content-type": "application/xml"},
        )

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    # Suppress the "Wave 1+ adds XML parsing" warning so filterwarnings=error
    # doesn't escalate it. We expect the warning — it's part of the contract.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
        results = await tool.search("q", agent_id="a", max_results=5)
    assert results == []


@pytest.mark.asyncio
async def test_brave_http_500_wraps(fake_redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key="k")
    with pytest.raises(WebSearchError, match="brave http error"):
        await tool.search("q", agent_id="a")


@pytest.mark.asyncio
async def test_brave_network_error_wraps(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network error")

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key="k")
    with pytest.raises(WebSearchError, match="brave network error"):
        await tool.search("q", agent_id="a")


@pytest.mark.asyncio
async def test_yandex_network_error_wraps(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated yandex fail")

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    with pytest.raises(WebSearchError, match="yandex network error"):
        await tool.search("q", agent_id="a")


@pytest.mark.asyncio
async def test_yandex_http_error_wraps(fake_redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "denied"})

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    with pytest.raises(WebSearchError, match="yandex http error"):
        await tool.search("q", agent_id="a")


@pytest.mark.asyncio
async def test_max_results_zero_rejected(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key="k")
    with pytest.raises(WebSearchError, match="max_results"):
        await tool.search("q", agent_id="a", max_results=0)


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-agent rate limit kicks in even for mock-mode."""
    monkeypatch.setenv("WEB_SEARCH_MOCK_MODE", "true")
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, limit_per_min=2)
    await tool.search("q1", agent_id="a")
    await tool.search("q2", agent_id="a")
    with pytest.raises(ToolRateLimitExceeded):
        await tool.search("q3", agent_id="a")


@pytest.mark.asyncio
async def test_env_var_picked_up_when_not_passed(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRAVE_SEARCH_API_KEY env-var hydrates the brave_api_key."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"web": {"results": []}})

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "env-key")
    monkeypatch.delenv("YANDEX_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter)  # no explicit kwargs
    results = await tool.search("anything", agent_id="agent-1")
    assert results == []
