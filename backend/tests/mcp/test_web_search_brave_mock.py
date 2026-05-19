"""Unit: WebSearchTool — Brave Search parsing + mock-mode short-circuit."""

from __future__ import annotations

import httpx
import pytest
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.mcp.tools.web_search import WebSearchResult, WebSearchTool

BRAVE_SAMPLE_PAYLOAD = {
    "web": {
        "results": [
            {
                "title": "First result",
                "url": "https://example.test/a",
                "description": "First snippet",
            },
            {
                "title": "Second result",
                "url": "https://example.test/b",
                "description": "Second snippet",
            },
        ],
    },
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
async def test_brave_search_parses_results(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("X-Subscription-Token")
        return httpx.Response(200, json=BRAVE_SAMPLE_PAYLOAD)

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    # Ensure mock-mode is off so we exercise the Brave path.
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter,
        brave_api_key="test-brave-key",
        yandex_api_key=None,
    )
    results = await tool.search("oriion roadmap", agent_id="agent-1", max_results=2)

    assert len(results) == 2
    assert results[0] == WebSearchResult(
        title="First result",
        url="https://example.test/a",
        snippet="First snippet",
    )
    assert captured["api_key"] == "test-brave-key"
    assert "q=oriion+roadmap" in str(captured["url"]) or "q=oriion%20roadmap" in str(
        captured["url"]
    )


@pytest.mark.asyncio
async def test_brave_search_handles_empty_payload(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key="k")
    results = await tool.search("foo", agent_id="agent-1")
    assert results == []


@pytest.mark.asyncio
async def test_mock_mode_returns_canned_results(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WEB_SEARCH_MOCK_MODE=true → canned results without network call."""
    monkeypatch.setenv("WEB_SEARCH_MOCK_MODE", "true")
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter,
        brave_api_key=None,
        yandex_api_key=None,
    )
    results = await tool.search("foo", agent_id="agent-1", max_results=3)
    assert len(results) == 3
    for r in results:
        assert "foo" in r.title.lower() or "foo" in r.snippet.lower()
        assert r.url.startswith("https://example.test/")


@pytest.mark.asyncio
async def test_mock_mode_yes_value(fake_redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock-mode env-var accepts 1/true/yes/on; bare empty string is OFF."""
    monkeypatch.setenv("WEB_SEARCH_MOCK_MODE", "yes")
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter)
    results = await tool.search("bar", agent_id="agent-1", max_results=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_empty_query_rejected(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key="k")
    from src.mcp.exceptions import WebSearchError

    with pytest.raises(WebSearchError):
        await tool.search("   ", agent_id="agent-1")
