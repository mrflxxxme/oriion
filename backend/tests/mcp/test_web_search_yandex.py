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


_YANDEX_XML_PAYLOAD = b"""<?xml version="1.0" encoding="utf-8"?>
<yandexsearch version="1.0">
  <response>
    <results>
      <grouping>
        <group>
          <doc>
            <url>https://example.test/y1</url>
            <title>\xd0\x97\xd0\xb0\xd0\xb3\xd0\xbe\xd0\xbb\xd0\xbe\xd0\xb2\xd0\xbe\xd0\xba <hlword>\xd0\xbe\xd0\xb4\xd0\xb8\xd0\xbd</hlword></title>
            <passages><passage>\xd0\xa2\xd0\xb5\xd0\xba\xd1\x81\xd1\x82 <hlword>\xd1\x81\xd0\xbd\xd0\xb8\xd0\xbf\xd0\xbf\xd0\xb5\xd1\x82\xd0\xb0</hlword></passage></passages>
          </doc>
        </group>
        <group>
          <doc>
            <url>https://example.test/y2</url>
            <title>Second</title>
            <headline>Headline two</headline>
          </doc>
        </group>
      </grouping>
    </results>
  </response>
</yandexsearch>
"""


@pytest.mark.asyncio
async def test_yandex_xml_response_parsed(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-W1-18: live Yandex XML is parsed (url + flattened title + passage)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_YANDEX_XML_PAYLOAD,
            headers={"content-type": "application/xml"},
        )

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    results = await tool.search("q", agent_id="a", max_results=5)

    assert len(results) == 2
    assert results[0].url == "https://example.test/y1"
    # <hlword> highlight markup flattened into the title text.
    assert results[0].title == "Заголовок один"
    assert results[0].snippet == "Текст сниппета"
    # Second doc has no passage → falls back to <headline>.
    assert results[1].url == "https://example.test/y2"
    assert results[1].snippet == "Headline two"


@pytest.mark.asyncio
async def test_yandex_xml_error_returns_empty(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Yandex <error> element degrades to [] (Researcher falls back to LLM)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(
                b'<?xml version="1.0"?><yandexsearch><response>'
                b'<error code="55">no rights</error></response></yandexsearch>'
            ),
            headers={"content-type": "application/xml"},
        )

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    assert await tool.search("q", agent_id="a", max_results=5) == []


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


@pytest.mark.asyncio
async def test_search_body_size_cap_enforced(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An over-cap response body is aborted (memory-DoS guard) — audit P2."""
    big = b"<yandexsearch>" + (b"x" * (6 * 1024 * 1024)) + b"</yandexsearch>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=big, headers={"content-type": "application/xml"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    with pytest.raises(WebSearchError, match="exceeded"):
        await tool.search("q", agent_id="a", max_results=5)


@pytest.mark.asyncio
async def test_yandex_xml_truncated_returns_empty(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """recover=False: a truncated/partial XML body degrades to [] rather than
    surfacing a half-streamed <title> as a real (mangled) hit — audit P3(b)."""
    truncated = (
        b'<?xml version="1.0"?><yandexsearch><response><results><grouping><group>'
        b"<doc><url>https://example.test/a</url><title>Tru"  # cut mid-title, unclosed
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=truncated, headers={"content-type": "application/xml"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    assert await tool.search("q", agent_id="a", max_results=5) == []


@pytest.mark.asyncio
async def test_yandex_xml_nested_error_does_not_nuke_results(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An element merely named <error> nested inside a valid <doc> must NOT
    discard the whole result set — the failure check is anchored to
    response/error, not a descendant .//error — audit P3(a)."""
    xml = (
        b'<?xml version="1.0"?><yandexsearch><response><results><grouping>'
        b"<group><doc><url>https://example.test/ok</url><title>Fine</title>"
        b"<properties><error>0</error></properties></doc></group>"
        b"</grouping></results></response></yandexsearch>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=xml, headers={"content-type": "application/xml"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key=None, yandex_api_key="k")
    results = await tool.search("q", agent_id="a", max_results=5)
    assert len(results) == 1
    assert results[0].url == "https://example.test/ok"
    assert results[0].title == "Fine"
