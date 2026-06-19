"""Regression: read_url DNS-rebinding pin + per-hop SSRF re-validation.

Audit P2 (2026-06-18): the SSRF guard resolved the host to reject private IPs,
then handed the raw hostname to httpx which RE-RESOLVED at connect (TOCTOU) — a
malicious resolver could answer a public IP to the check and 169.254.169.254 to
httpx. The fix resolves once to a vetted IP and pins the connection to it while
keeping the hostname for Host + TLS-cert (sni_hostname).
"""

from __future__ import annotations

import socket
from collections.abc import Callable

import httpx
import pytest
from src.mcp.exceptions import ReadURLError
from src.mcp.tools import read_url as ru
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.mcp.tools.read_url import ReadURLTool, _resolve_vetted_ip


def _fake_getaddrinfo(*ips: str) -> Callable[..., list[tuple[object, ...]]]:
    def _inner(host: object, *_a: object, **_k: object) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0)) for ip in ips]

    return _inner


def _install_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    original = httpx.AsyncClient

    def patched(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("src.mcp.tools.read_url.httpx.AsyncClient", patched)


# ── _resolve_vetted_ip unit ──────────────────────────────────────────────


def test_resolve_vetted_ip_returns_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ru.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    assert _resolve_vetted_ip("example.com") == "93.184.216.34"


def test_resolve_vetted_ip_rejects_private_literal() -> None:
    with pytest.raises(ReadURLError, match="private/loopback"):
        _resolve_vetted_ip("169.254.169.254")


def test_resolve_vetted_ip_rejects_any_private_in_multi_a(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multi-A rebinding: one public + one private answer → reject the whole host."""
    monkeypatch.setattr(
        ru.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34", "169.254.169.254")
    )
    with pytest.raises(ReadURLError, match="private/loopback"):
        _resolve_vetted_ip("rebind.example")


def test_resolve_vetted_ip_fail_closed_on_dns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> object:
        raise OSError("nxdomain")

    monkeypatch.setattr(ru.socket, "getaddrinfo", _raise)
    with pytest.raises(ReadURLError, match="DNS resolution failed"):
        _resolve_vetted_ip("nope.example")


# ── fetch pins the connection to the vetted IP ────────────────────────────


@pytest.mark.asyncio
async def test_fetch_pins_connection_to_vetted_ip(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["host"] = request.url.host
        captured["host_header"] = request.headers.get("host")
        captured["sni"] = request.extensions.get("sni_hostname")
        return httpx.Response(
            200, content=b"<html><body>hi</body></html>", headers={"content-type": "text/html"}
        )

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.setattr(ru.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    monkeypatch.setattr(ru, "_extract_with_readability", lambda _html: ("t", "body"))

    tool = ReadURLTool(rate_limiter=ToolRateLimiter(redis=fake_redis))  # type: ignore[arg-type]
    result = await tool.fetch("https://news.example/a", agent_id="x")

    assert captured["host"] == "93.184.216.34"  # connected to the vetted IP, not the hostname
    assert captured["host_header"] == "news.example"  # Host header keeps the original hostname
    assert captured["sni"] == "news.example"  # TLS cert verified against the hostname via SNI
    assert result.url == "https://news.example/a"  # the logical (hostname) URL is reported


@pytest.mark.asyncio
async def test_fetch_rejects_redirect_to_internal_host(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A redirect to the cloud-metadata IP is re-validated per hop and refused."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.setattr(ru.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))

    tool = ReadURLTool(rate_limiter=ToolRateLimiter(redis=fake_redis))  # type: ignore[arg-type]
    with pytest.raises(ReadURLError, match="private/loopback"):
        await tool.fetch("https://news.example/start", agent_id="x")
