"""Unit: ReadURLTool — content extraction + size cap + SSRF guard + scheme.

Uses httpx.MockTransport for HTTP stubbing (no extra dep beyond httpx
itself; pytest-httpx / respx will be added by main agent in Step 4 but
this test is self-contained so a missing optional dep does not block it).

`readability-lxml` is the only optional dep — we `importorskip` so the
test gracefully skips when the package is not yet installed.
"""

from __future__ import annotations

import httpx
import pytest

# Skip the whole module if readability-lxml or lxml are not installed —
# main agent adds them in Step 4 of the combined 00.3+00.4 PR.
pytest.importorskip("readability")
pytest.importorskip("lxml")

from src.mcp.exceptions import ReadURLError  # noqa: E402
from src.mcp.tools.rate_limit import ToolRateLimiter  # noqa: E402
from src.mcp.tools.read_url import (  # noqa: E402
    ReadURLTool,
    _is_private_ip,
    _validate_url,
)

# ── HTML fixtures ─────────────────────────────────────────────────────────


SAMPLE_HTML = """
<!doctype html>
<html lang="en">
  <head><title>The Test Article Title</title></head>
  <body>
    <header>nav</header>
    <article>
      <h1>The Test Article Title</h1>
      <p>This is the main article body that readability should extract.
         It contains enough words for the extractor to consider it the
         primary content of the page rather than chrome.</p>
      <p>A second paragraph with meaningful content also helps the
         density score favour this region of the document.</p>
    </article>
    <footer>copyright</footer>
  </body>
</html>
"""


def _build_tool_with_transport(
    transport: httpx.MockTransport,
    fake_redis: object,
) -> ReadURLTool:
    """Build a ReadURLTool that uses a given MockTransport for httpx calls.

    We monkey-patch the AsyncClient via a subclass so the production
    `async with httpx.AsyncClient(...)` still picks up our transport
    without touching the network.
    """
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    # Bind transport via the closure on a subclass of AsyncClient that
    # injects it automatically. ReadURLTool calls httpx.AsyncClient(...)
    # directly, so we replace the symbol in the module under test.
    return tool


# ── Helpers for SSRF guard tests ──────────────────────────────────────────


def test_is_private_ip_covers_rfc1918() -> None:
    assert _is_private_ip("10.0.0.1") is True
    assert _is_private_ip("172.16.0.1") is True
    assert _is_private_ip("192.168.1.1") is True
    assert _is_private_ip("127.0.0.1") is True
    assert _is_private_ip("169.254.169.254") is True
    assert _is_private_ip("0.0.0.0") is True
    assert _is_private_ip("8.8.8.8") is False


def test_is_private_ip_handles_garbage() -> None:
    assert _is_private_ip("not-an-ip") is False


def test_validate_url_rejects_non_http_scheme() -> None:
    with pytest.raises(ReadURLError, match="unsupported scheme"):
        _validate_url("ftp://example.com/file")
    with pytest.raises(ReadURLError, match="unsupported scheme"):
        _validate_url("file:///etc/passwd")
    with pytest.raises(ReadURLError, match="unsupported scheme"):
        _validate_url("data:text/plain,hello")


def test_validate_url_rejects_loopback_literal() -> None:
    with pytest.raises(ReadURLError, match="private/loopback"):
        _validate_url("http://127.0.0.1/")


def test_validate_url_rejects_rfc1918_literal() -> None:
    with pytest.raises(ReadURLError, match="private/loopback"):
        _validate_url("http://10.0.0.1/admin")
    with pytest.raises(ReadURLError, match="private/loopback"):
        _validate_url("http://192.168.1.1/")
    with pytest.raises(ReadURLError, match="private/loopback"):
        _validate_url("http://169.254.169.254/latest/meta-data/")


def test_validate_url_requires_hostname() -> None:
    with pytest.raises(ReadURLError, match="hostname"):
        _validate_url("http:///nopath")


# ── Extraction tests (use MockTransport) ─────────────────────────────────


@pytest.mark.asyncio
async def test_read_url_extracts_title_and_main_content(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Happy path: response body → readability → title + text."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=SAMPLE_HTML.encode("utf-8"),
            headers={"content-type": "text/html; charset=utf-8"},
        )

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    # Bypass DNS-based SSRF guard for the public example URL — getaddrinfo
    # in CI may hit external DNS; force the hostname-resolves check to
    # return False so we exercise the extraction path deterministically.
    monkeypatch.setattr("src.mcp.tools.read_url._hostname_resolves_to_private", lambda h: False)
    monkeypatch.setattr("src.mcp.tools.read_url._resolve_vetted_ip", lambda h: "93.184.216.34")

    result = await tool.fetch("https://example.test/article", agent_id="agent-1")

    assert "Test Article Title" in result.title
    assert "main article body" in result.text_content
    assert result.url == "https://example.test/article"
    assert result.fetched_at is not None


@pytest.mark.asyncio
async def test_read_url_enforces_5mb_cap(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Server sending > 5 MB body must raise ReadURLError."""

    big_chunk = b"x" * (1024 * 1024)  # 1 MB

    def handler(request: httpx.Request) -> httpx.Response:
        # 6 MB body: 6 x 1 MB chunks.
        return httpx.Response(
            200,
            content=big_chunk * 6,
            headers={"content-type": "text/html"},
        )

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter, max_body_bytes=5 * 1024 * 1024)
    monkeypatch.setattr("src.mcp.tools.read_url._hostname_resolves_to_private", lambda h: False)
    monkeypatch.setattr("src.mcp.tools.read_url._resolve_vetted_ip", lambda h: "93.184.216.34")
    with pytest.raises(ReadURLError, match="exceeded"):
        await tool.fetch("https://example.test/huge", agent_id="agent-1")


@pytest.mark.asyncio
async def test_read_url_refuses_loopback(fake_redis: object) -> None:
    """SSRF guard kicks in before any network call."""
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    with pytest.raises(ReadURLError, match="private/loopback"):
        await tool.fetch("http://127.0.0.1/", agent_id="agent-1")


@pytest.mark.asyncio
async def test_read_url_refuses_rfc1918(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    with pytest.raises(ReadURLError, match="private/loopback"):
        await tool.fetch("http://10.0.0.1/", agent_id="agent-1")


@pytest.mark.asyncio
async def test_read_url_refuses_non_http(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    with pytest.raises(ReadURLError, match="unsupported scheme"):
        await tool.fetch("file:///etc/passwd", agent_id="agent-1")


@pytest.mark.asyncio
async def test_read_url_network_error_wraps_into_read_url_error(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network error")

    transport = httpx.MockTransport(handler)
    _install_transport(monkeypatch, transport)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    monkeypatch.setattr("src.mcp.tools.read_url._hostname_resolves_to_private", lambda h: False)
    monkeypatch.setattr("src.mcp.tools.read_url._resolve_vetted_ip", lambda h: "93.184.216.34")
    with pytest.raises(ReadURLError, match="network error"):
        await tool.fetch("https://example.test/", agent_id="agent-1")


# ── Transport plumbing ────────────────────────────────────────────────────


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    transport: httpx.MockTransport,
) -> None:
    """Monkey-patch httpx.AsyncClient to inject our MockTransport.

    ReadURLTool builds the AsyncClient with kwargs; we wrap the class so
    the `transport=` kwarg gets injected on construction without touching
    production code.
    """
    original = httpx.AsyncClient

    def patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("src.mcp.tools.read_url.httpx.AsyncClient", patched)
