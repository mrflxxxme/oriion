"""`read_url` built-in tool — fetch a URL + extract main content.

Phase 00.4 § Task 14 — 10 req/min per agent_id. Returns title +
text_content extracted via `readability-lxml` from the fetched body.

Safety controls
---------------
* **Scheme allow-list**: http / https only. Refuses ``file://``,
  ``ftp://``, ``data:``, etc. — anything that could escape the network
  boundary or read local files.
* **5 MB max body size**: streamed download with running counter. Aborts
  + raises ``ReadURLError`` if the server tries to deliver more (large
  binaries, log endpoints, etc.). Protects worker memory.
* **SSRF guard + DNS-rebinding pin**: the host is resolved **once** to a
  vetted public IP (RFC 1918 / loopback / link-local / reserved IPs are
  refused), and the connection is **pinned to that exact IP** — httpx is
  handed the IP as the connect target while the original hostname is kept
  for SNI + TLS-cert verification (``sni_hostname``) and the ``Host``
  header. This closes the TOCTOU window where a malicious resolver could
  answer a public IP to the guard's lookup, then ``169.254.169.254`` /
  ``127.0.0.1`` to httpx's own re-resolution at connect time. Reachable
  now that the Researcher LLM can pick URLs from web-search content.
* **5s timeout**: total request budget — connect + read combined.

Redirects are followed **manually** (``follow_redirects=False``) so every
hop is re-resolved, re-validated and re-pinned — a 303 → an internal host
is caught, and the redirect chain is capped.

Wave 1+ hardening (still deferred per phase scope):
    * Robots.txt + content-type allow-list.
    * Per-cell egress allow-list (rbac integration).
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from urllib.parse import urlparse

import httpx
import structlog

from src.mcp.exceptions import ReadURLError, ToolRateLimitExceeded
from src.mcp.tools.rate_limit import ToolRateLimiter

logger = structlog.get_logger(__name__)

_TOOL_NAME: Final = "read_url"
_DEFAULT_LIMIT_PER_MIN: Final = 10
_DEFAULT_WINDOW_SECONDS: Final = 60
_DEFAULT_TIMEOUT_SECONDS: Final = 5.0
_MAX_BODY_BYTES: Final = 5 * 1024 * 1024  # 5 MB
_MAX_REDIRECTS: Final = 5
_ALLOWED_SCHEMES: Final = frozenset({"http", "https"})


@dataclass(frozen=True, slots=True)
class ReadURLResult:
    """Successful fetch + extraction result."""

    url: str
    title: str
    text_content: str
    fetched_at: datetime


def _is_private_ip(ip: str) -> bool:
    """Return True for RFC 1918 / loopback / link-local / multicast IPs.

    SSRF guard — these address ranges represent the host's own networks,
    so a fetch against them risks exfiltrating internal-only services.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _hostname_resolves_to_private(host: str) -> bool:
    """DNS-resolve a hostname and check whether any returned IP is private.

    Used as the static pre-flight check in :func:`_validate_url` (cheap reject
    of an obviously-private literal/host). The authoritative anti-rebinding
    control is :func:`_resolve_vetted_ip`, which resolves once and pins the
    connection to the vetted IP. A DNS failure here is non-fatal (returns
    False) — the pin resolve surfaces the hard error.
    """
    # If the host *is* an IP literal, check directly without DNS.
    try:
        ipaddress.ip_address(host)
        return _is_private_ip(host)
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = str(info[4][0])
        if _is_private_ip(ip):
            return True
    return False


def _validate_url(url: str) -> None:
    """Raises ReadURLError if URL fails scheme allow-list or SSRF pre-check."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ReadURLError(f"unsupported scheme {parsed.scheme!r}: only http/https allowed")
    if not parsed.hostname:
        raise ReadURLError("URL must include a hostname")
    if _hostname_resolves_to_private(parsed.hostname):
        raise ReadURLError(f"refusing to fetch private/loopback address: {parsed.hostname}")


def _resolve_vetted_ip(host: str) -> str:
    """Resolve ``host`` to a single public IP and return it, or raise ReadURLError.

    Anti-rebinding pin: the caller connects to *this exact IP* rather than
    re-resolving the hostname, so a resolver that flips its answer to a private
    IP between the check and httpx's connect cannot bypass the guard. Rejects if
    **any** resolved address is private (defeats round-robin / multi-A rebinding)
    and raises on an unresolvable host (fail-closed — unlike the soft pre-check).
    """
    # IP literal: classify directly, no DNS.
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if _is_private_ip(host):
            raise ReadURLError(f"refusing to fetch private/loopback address: {host}")
        return host

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ReadURLError(f"DNS resolution failed for {host}") from exc
    ips = [str(info[4][0]) for info in infos]
    if not ips:
        raise ReadURLError(f"no addresses resolved for {host}")
    for ip in ips:
        if _is_private_ip(ip):
            raise ReadURLError(f"refusing to fetch private/loopback address: {host} -> {ip}")
    return ips[0]


def _host_header(url: httpx.URL) -> str:
    """The ``Host`` header authority (host[:port], IPv6 bracketed) — without
    userinfo, and using the original hostname (not the pinned IP)."""
    host = url.host
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    return host if url.port is None else f"{host}:{url.port}"


def _extract_with_readability(html: str) -> tuple[str, str]:
    """Return (title, text_content) from raw HTML.

    Imported lazily so the rest of the module loads without
    readability-lxml installed (Wave 0 dep added by main agent in Step 4).
    Tests that exercise extraction guard imports via `pytest.importorskip`.
    """
    # Both modules are configured as ignore_missing_imports in
    # pyproject.toml [tool.mypy.overrides] — see Phase 00.4 deps block.
    from lxml import html as lxml_html
    from readability import Document

    doc = Document(html)
    title: str = (doc.short_title() or "").strip()
    # `summary()` returns an HTML snippet of the main article. Strip tags
    # for the text-content view we surface to the LLM.
    summary_html: str = doc.summary(html_partial=True)
    tree = lxml_html.fromstring(summary_html) if summary_html else None
    text_content = " ".join(tree.text_content().split()) if tree is not None else ""
    return title, text_content


class ReadURLTool:
    """Fetch + extract main content. Rate-limited per agent_id."""

    def __init__(
        self,
        rate_limiter: ToolRateLimiter,
        *,
        limit_per_min: int = _DEFAULT_LIMIT_PER_MIN,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_body_bytes: int = _MAX_BODY_BYTES,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._limit_per_min = limit_per_min
        self._timeout_seconds = timeout_seconds
        self._max_body_bytes = max_body_bytes

    async def fetch(self, url: str, agent_id: str = "system") -> ReadURLResult:
        """Fetch + extract. Raises ReadURLError on any failure path.

        Rate-limit is checked first — exhaustion raises
        ``ToolRateLimitExceeded`` so the caller can surface 429 without
        burning network round-trip budget.
        """
        # Rate limit gate ----------------------------------------------------
        verdict = await self._rate_limiter.check_detailed(
            agent_id=agent_id,
            tool_name=_TOOL_NAME,
            limit=self._limit_per_min,
            window_seconds=_DEFAULT_WINDOW_SECONDS,
        )
        if not verdict.allowed:
            raise ToolRateLimitExceeded(
                retry_after=verdict.retry_after,
                detail=f"read_url limit {self._limit_per_min}/min exceeded",
            )

        # Static pre-flight (scheme + hostname + obvious-private literal) -----
        _validate_url(url)

        # Fetch with per-hop resolve-validate-pin ----------------------------
        return await self._fetch_pinned(url, agent_id)

    async def _fetch_pinned(self, url: str, agent_id: str) -> ReadURLResult:
        """Follow redirects manually; each hop is resolved to a vetted IP and
        the connection is pinned to it (Host + SNI keep the original hostname)."""
        timeout = httpx.Timeout(self._timeout_seconds)
        logical_url = httpx.URL(url)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            for hop in range(_MAX_REDIRECTS + 1):
                if logical_url.scheme.lower() not in _ALLOWED_SCHEMES:
                    raise ReadURLError(
                        f"unsupported scheme {logical_url.scheme!r}: only http/https allowed"
                    )
                host = logical_url.host
                if not host:
                    raise ReadURLError("URL must include a hostname")

                vetted_ip = _resolve_vetted_ip(host)
                connect_url = logical_url.copy_with(host=vetted_ip)
                request = client.build_request(
                    "GET",
                    connect_url,
                    headers={"Host": _host_header(logical_url)},
                    # Pin TLS SNI + cert verification to the real hostname even
                    # though we connect to the literal IP (httpcore reads this).
                    extensions={"sni_hostname": host},
                )
                try:
                    response = await client.send(request, stream=True)
                except httpx.RequestError as exc:
                    raise ReadURLError(f"network error: {exc!s}") from exc

                try:
                    if response.is_redirect:
                        if hop >= _MAX_REDIRECTS:
                            raise ReadURLError(f"too many redirects (>{_MAX_REDIRECTS})")
                        location = response.headers.get("location")
                        if not location:
                            raise ReadURLError("redirect response missing Location header")
                        logical_url = logical_url.join(location)
                        continue
                    response.raise_for_status()
                    body, total = await self._read_capped(response)
                    encoding = response.encoding or "utf-8"
                except httpx.HTTPStatusError as exc:
                    raise ReadURLError(
                        f"http error: {exc.response.status_code} {exc.response.reason_phrase}"
                    ) from exc
                finally:
                    await response.aclose()

                return self._build_result(body, encoding, str(logical_url), agent_id, total)

        raise ReadURLError(f"too many redirects (>{_MAX_REDIRECTS})")  # pragma: no cover

    async def _read_capped(self, response: httpx.Response) -> tuple[bytes, int]:
        """Stream the body, aborting past the size cap."""
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self._max_body_bytes:
                raise ReadURLError(f"response exceeded {self._max_body_bytes} bytes cap")
            chunks.append(chunk)
        return b"".join(chunks), total

    def _build_result(
        self, body: bytes, encoding: str, final_url: str, agent_id: str, total: int
    ) -> ReadURLResult:
        try:
            html_text = body.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            html_text = body.decode("utf-8", errors="replace")

        try:
            title, text_content = _extract_with_readability(html_text)
        except Exception as exc:
            raise ReadURLError(f"content extraction failed: {exc!s}") from exc

        result = ReadURLResult(
            url=final_url,
            title=title,
            text_content=text_content,
            fetched_at=datetime.now(UTC),
        )
        logger.info(
            "mcp.tools.read_url.fetched",
            url=final_url,
            agent_id=agent_id,
            bytes=total,
            title_len=len(title),
            text_len=len(text_content),
        )
        return result
