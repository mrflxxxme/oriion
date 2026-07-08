"""Unit: WebSearchTool — Yandex Cloud Search API v2 (async) + Brave→Yandex fallback.

The Yandex backend is the async v2 flow (module docstring): POST /v2/web/searchAsync
returns an operation id → poll the Operation API until done → base64-decode the XML
in response.rawData → parse with the existing `<yandexsearch>` parser. Tests mock
both hops via httpx.MockTransport routed by host.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
from src.mcp.exceptions import ToolRateLimitExceeded, WebSearchError
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.mcp.tools.web_search import WebSearchTool

_SEARCHAPI_HOST = "searchapi.api.cloud.yandex.net"
_OPERATION_HOST = "operation.api.cloud.yandex.net"
_BRAVE_HOST = "api.search.brave.com"


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    transport: httpx.MockTransport,
) -> None:
    original = httpx.AsyncClient

    def patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("src.mcp.tools.web_search.httpx.AsyncClient", patched)


def _no_poll_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero the inter-poll sleep so the async v2 flow runs instantly in tests."""
    monkeypatch.setattr("src.mcp.tools.web_search._YANDEX_POLL_INTERVAL_SECONDS", 0.0)


def _yandex_v2_handler(
    raw_xml: bytes,
    *,
    op_id: str = "op-abc123",
    captured: dict[str, Any] | None = None,
    poll_done_after: int = 1,
) -> Any:
    """Handler emulating the v2 async flow: submit → op id, poll → done+rawData."""
    state = {"polls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == _SEARCHAPI_HOST:
            if captured is not None:
                captured["submit_method"] = request.method
                captured["submit_url"] = str(request.url)
                captured["submit_auth"] = request.headers.get("authorization")
                captured["submit_body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": op_id, "done": False})
        if host == _OPERATION_HOST:
            state["polls"] += 1
            if captured is not None:
                captured["poll_auth"] = request.headers.get("authorization")
                captured.setdefault("poll_urls", []).append(str(request.url))
            if state["polls"] < poll_done_after:
                return httpx.Response(200, json={"done": False})
            return httpx.Response(
                200,
                json={
                    "done": True,
                    "response": {"rawData": base64.b64encode(raw_xml).decode("ascii")},
                },
            )
        raise AssertionError(f"unexpected host {host!r}")

    return handler


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
async def test_yandex_v2_used_when_brave_unset_and_request_built_with_modern_auth(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No Brave key + Yandex key/folder set → the modern v2 async path runs.

    Asserts the submit hits /v2/web/searchAsync with an `Authorization: Api-Key`
    header and a JSON body carrying folderId + query.queryText + groupsOnPage,
    and that polling targets the Operation API with the same auth.
    """
    captured: dict[str, Any] = {}
    transport = httpx.MockTransport(_yandex_v2_handler(_YANDEX_XML_PAYLOAD, captured=captured))
    _install_transport(monkeypatch, transport)
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter,
        brave_api_key=None,
        yandex_api_key="test-yandex",
        yandex_folder_id="folder-42",
    )
    results = await tool.search("привет", agent_id="agent-1", max_results=2)

    assert len(results) == 2
    assert results[0].url == "https://example.test/y1"
    # Modern auth: Api-Key header (NOT the dead user/key query params).
    assert captured["submit_method"] == "POST"
    assert _SEARCHAPI_HOST in captured["submit_url"]
    assert captured["submit_auth"] == "Api-Key test-yandex"
    body = captured["submit_body"]
    assert body["folderId"] == "folder-42"
    assert body["query"]["queryText"] == "привет"
    assert body["groupSpec"]["groupsOnPage"] == 2
    # Poll targeted the Operation API with the op id and the same auth.
    assert captured["poll_auth"] == "Api-Key test-yandex"
    assert any("op-abc123" in u and _OPERATION_HOST in u for u in captured["poll_urls"])


@pytest.mark.asyncio
async def test_yandex_v2_xml_response_parsed(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """base64 rawData XML is decoded + parsed (url + flattened title + passage)."""
    transport = httpx.MockTransport(_yandex_v2_handler(_YANDEX_XML_PAYLOAD))
    _install_transport(monkeypatch, transport)
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
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
async def test_yandex_v2_polls_until_done(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A not-yet-done operation is polled again until done=true."""
    handler = _yandex_v2_handler(_YANDEX_XML_PAYLOAD, poll_done_after=3)
    _install_transport(monkeypatch, httpx.MockTransport(handler))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
    results = await tool.search("q", agent_id="a", max_results=5)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_yandex_v2_poll_timeout_raises(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An operation that never completes raises WebSearchError (bounded poll)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == _SEARCHAPI_HOST:
            return httpx.Response(200, json={"id": "op-x", "done": False})
        return httpx.Response(200, json={"done": False})  # never done

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
    with pytest.raises(WebSearchError, match="poll timed out"):
        await tool.search("q", agent_id="a", max_results=5)


@pytest.mark.asyncio
async def test_yandex_v2_xml_error_returns_empty(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Yandex <error> element in rawData degrades to [] (Researcher → LLM)."""
    error_xml = (
        b'<?xml version="1.0"?><yandexsearch><response>'
        b'<error code="55">no rights</error></response></yandexsearch>'
    )
    _install_transport(monkeypatch, httpx.MockTransport(_yandex_v2_handler(error_xml)))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
    assert await tool.search("q", agent_id="a", max_results=5) == []


@pytest.mark.asyncio
async def test_yandex_folder_id_missing_raises(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yandex key set but no folder id (YANDEX_CATALOG_ID) → WebSearchError."""
    monkeypatch.delenv("YANDEX_CATALOG_ID", raising=False)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id=None
    )
    with pytest.raises(WebSearchError, match="yandex_folder_id"):
        await tool.search("q", agent_id="a", max_results=5)


@pytest.mark.asyncio
async def test_brave_failure_falls_back_to_yandex(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Brave configured but failing (HTTP 500) + Yandex configured → fall back
    to the Yandex v2 path and return its results."""
    yandex_handler = _yandex_v2_handler(_YANDEX_XML_PAYLOAD)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == _BRAVE_HOST:
            return httpx.Response(500, json={"error": "boom"})
        return yandex_handler(request)

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter,
        brave_api_key="brave-k",
        yandex_api_key="yandex-k",
        yandex_folder_id="f",
    )
    results = await tool.search("q", agent_id="a", max_results=5)
    assert len(results) == 2
    assert results[0].url == "https://example.test/y1"


@pytest.mark.asyncio
async def test_brave_network_error_falls_back_to_yandex(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Brave *network* error also triggers the Yandex fallback."""
    yandex_handler = _yandex_v2_handler(_YANDEX_XML_PAYLOAD)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == _BRAVE_HOST:
            raise httpx.ConnectError("brave down")
        return yandex_handler(request)

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter,
        brave_api_key="brave-k",
        yandex_api_key="yandex-k",
        yandex_folder_id="f",
    )
    results = await tool.search("q", agent_id="a", max_results=5)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_both_backends_fail_raises_primary_brave_error(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When Brave AND the Yandex fallback both fail, the primary (Brave) error
    is surfaced (most-informative for the caller)."""

    def handler(request: httpx.Request) -> httpx.Response:
        # Brave 500 → "brave http error"; Yandex submit 503 → "yandex http error".
        if request.url.host == _BRAVE_HOST:
            return httpx.Response(500, json={"error": "brave"})
        return httpx.Response(503, json={"error": "yandex"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter,
        brave_api_key="brave-k",
        yandex_api_key="yandex-k",
        yandex_folder_id="f",
    )
    with pytest.raises(WebSearchError, match="brave http error"):
        await tool.search("q", agent_id="a", max_results=5)


@pytest.mark.asyncio
async def test_brave_failure_no_yandex_reraises(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Brave fails and NO Yandex key configured → the Brave error propagates
    (no fallback attempted)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter, brave_api_key="k", yandex_api_key=None)
    with pytest.raises(WebSearchError, match="brave http error"):
        await tool.search("q", agent_id="a")


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
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
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
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
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
    """An over-cap response body is aborted (memory-DoS guard) — audit P2.

    Here the v2 submit response itself is over-cap → the stream is aborted.
    """
    big = b"{" + (b"x" * (6 * 1024 * 1024)) + b"}"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=big, headers={"content-type": "application/json"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
    with pytest.raises(WebSearchError, match="exceeded"):
        await tool.search("q", agent_id="a", max_results=5)


@pytest.mark.asyncio
async def test_yandex_xml_truncated_returns_empty(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """recover=False: a truncated/partial XML body in rawData degrades to []
    rather than surfacing a half-streamed <title> as a real hit — audit P3(b)."""
    truncated = (
        b'<?xml version="1.0"?><yandexsearch><response><results><grouping><group>'
        b"<doc><url>https://example.test/a</url><title>Tru"  # cut mid-title, unclosed
    )
    _install_transport(monkeypatch, httpx.MockTransport(_yandex_v2_handler(truncated)))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
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
    _install_transport(monkeypatch, httpx.MockTransport(_yandex_v2_handler(xml)))
    _no_poll_delay(monkeypatch)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(
        rate_limiter=limiter, brave_api_key=None, yandex_api_key="k", yandex_folder_id="f"
    )
    results = await tool.search("q", agent_id="a", max_results=5)
    assert len(results) == 1
    assert results[0].url == "https://example.test/ok"
    assert results[0].title == "Fine"
