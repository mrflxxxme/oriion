"""Unit: ReadURLTool — SSRF guard + scheme + rate-limit gate.

This file is INDEPENDENT of readability-lxml so the safety/validation
coverage path runs even before main agent installs that optional dep
(Step 4). The extraction-path tests live in
`test_read_url_extracts_main_content.py` (gated by `importorskip`).
"""

from __future__ import annotations

import pytest
from src.mcp.exceptions import ReadURLError, ToolRateLimitExceeded
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.mcp.tools.read_url import (
    ReadURLResult,
    ReadURLTool,
    _hostname_resolves_to_private,
    _is_private_ip,
    _validate_url,
)

# ── Pure-function helpers ────────────────────────────────────────────────


def test_is_private_ip_rfc1918() -> None:
    assert _is_private_ip("10.1.2.3") is True
    assert _is_private_ip("172.20.0.1") is True
    assert _is_private_ip("192.168.0.1") is True
    assert _is_private_ip("127.0.0.1") is True
    assert _is_private_ip("169.254.169.254") is True


def test_is_private_ip_public_addresses_pass() -> None:
    assert _is_private_ip("8.8.8.8") is False
    assert _is_private_ip("1.1.1.1") is False
    assert _is_private_ip("93.184.216.34") is False


def test_is_private_ip_handles_invalid_input() -> None:
    assert _is_private_ip("not-an-ip-at-all") is False
    assert _is_private_ip("") is False


def test_is_private_ip_handles_ipv6() -> None:
    assert _is_private_ip("::1") is True  # loopback
    assert _is_private_ip("fe80::1") is True  # link-local
    assert _is_private_ip("fc00::1") is True  # ULA (private)


def test_hostname_resolves_to_private_with_ip_literal() -> None:
    """When host is an IP literal, no DNS — just classify directly."""
    assert _hostname_resolves_to_private("127.0.0.1") is True
    assert _hostname_resolves_to_private("10.0.0.5") is True
    assert _hostname_resolves_to_private("8.8.8.8") is False


def test_hostname_resolves_to_private_dns_failure_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """getaddrinfo failure must NOT raise — return False instead."""

    def _raise(*args: object, **kwargs: object) -> object:
        raise OSError("simulated DNS fail")

    monkeypatch.setattr("src.mcp.tools.read_url.socket.getaddrinfo", _raise)
    assert _hostname_resolves_to_private("nonexistent.example.test") is False


def test_validate_url_rejects_schemes() -> None:
    for url in (
        "ftp://example.com/",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<h1>x</h1>",
    ):
        with pytest.raises(ReadURLError, match="unsupported scheme"):
            _validate_url(url)


def test_validate_url_rejects_loopback_and_rfc1918() -> None:
    for url in (
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/",
    ):
        with pytest.raises(ReadURLError, match="private/loopback"):
            _validate_url(url)


def test_validate_url_requires_hostname() -> None:
    with pytest.raises(ReadURLError, match="hostname"):
        _validate_url("https:///")


# ── ReadURLTool surface ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_blocks_loopback_before_network(fake_redis: object) -> None:
    """SSRF guard runs after the rate limit, but BEFORE the network call."""
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    with pytest.raises(ReadURLError, match="private/loopback"):
        await tool.fetch("http://127.0.0.1/", agent_id="agent-1")


@pytest.mark.asyncio
async def test_fetch_blocks_rfc1918(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    with pytest.raises(ReadURLError, match="private/loopback"):
        await tool.fetch("http://10.0.0.1/admin", agent_id="agent-1")


@pytest.mark.asyncio
async def test_fetch_rejects_non_http_scheme(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter)
    with pytest.raises(ReadURLError, match="unsupported scheme"):
        await tool.fetch("file:///etc/passwd", agent_id="agent-1")


@pytest.mark.asyncio
async def test_fetch_raises_rate_limit_after_limit_exceeded(
    fake_redis: object,
) -> None:
    """After 10 successful (rejected-at-SSRF) calls, the 11th should 429."""
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = ReadURLTool(rate_limiter=limiter, limit_per_min=2)
    # First two raise ReadURLError (SSRF) but count against the rate limit.
    for _ in range(2):
        with pytest.raises(ReadURLError):
            await tool.fetch("http://127.0.0.1/", agent_id="agent-x")
    # Third must hit the rate-limit gate first → ToolRateLimitExceeded.
    with pytest.raises(ToolRateLimitExceeded):
        await tool.fetch("http://127.0.0.1/", agent_id="agent-x")


def test_read_url_result_dataclass_immutable() -> None:
    from datetime import UTC, datetime

    result = ReadURLResult(
        url="https://example.test/",
        title="t",
        text_content="body",
        fetched_at=datetime.now(UTC),
    )
    with pytest.raises((AttributeError, TypeError)):
        result.url = "https://other.test/"  # type: ignore[misc]
