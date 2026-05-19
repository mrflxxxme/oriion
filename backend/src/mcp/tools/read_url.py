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
* **Basic SSRF guard**: pre-resolves the target host and refuses RFC 1918
  / loopback / link-local IPs. Mitigates the most common SSRF vector
  (asking us to fetch ``http://169.254.169.254/`` to exfil cloud creds, or
  ``http://10.0.0.1/`` to probe internal services).
* **5s timeout**: total request budget — connect + read combined.

The SSRF guard runs **on every redirect target** too — we set
``follow_redirects=True`` on httpx but enforce a custom event hook so a
303 → ``http://127.0.0.1/`` is caught.

Wave 1+ hardening (deferred per phase scope):
    * DNS-rebinding mitigation (resolve once + pass IP to httpx).
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

    A hostname pointing at ``127.0.0.1`` (DNS rebinding-lite) is rejected.
    If resolution itself fails we treat that as a hard error in the caller
    (the upstream request will fail anyway, but we surface a clear msg).
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
        # DNS failure — let the httpx call surface the real error; not our
        # responsibility to fail-closed here (rate-limit accounting already
        # done by the caller).
        return False
    for info in infos:
        sockaddr = info[4]
        ip_raw = sockaddr[0]
        # IPv6 sockaddr has 4 elements; IPv4 has 2. First is always the string IP.
        ip = str(ip_raw)
        if _is_private_ip(ip):
            return True
    return False


def _validate_url(url: str) -> None:
    """Raises ReadURLError if URL fails scheme allow-list or SSRF guard."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ReadURLError(f"unsupported scheme {parsed.scheme!r}: only http/https allowed")
    if not parsed.hostname:
        raise ReadURLError("URL must include a hostname")
    if _hostname_resolves_to_private(parsed.hostname):
        raise ReadURLError(f"refusing to fetch private/loopback address: {parsed.hostname}")


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

        # Pre-flight URL validation -----------------------------------------
        _validate_url(url)

        # Fetch + size-cap streaming -----------------------------------------
        timeout = httpx.Timeout(self._timeout_seconds)
        try:
            async with (
                httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    event_hooks={"response": [self._guard_redirect]},
                ) as client,
                client.stream("GET", url) as response,
            ):
                response.raise_for_status()
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > self._max_body_bytes:
                        raise ReadURLError(f"response exceeded {self._max_body_bytes} bytes cap")
                    chunks.append(chunk)
                body = b"".join(chunks)
                encoding = response.encoding or "utf-8"
                final_url = str(response.url)
        except httpx.RequestError as exc:
            raise ReadURLError(f"network error: {exc!s}") from exc
        except httpx.HTTPStatusError as exc:
            raise ReadURLError(
                f"http error: {exc.response.status_code} {exc.response.reason_phrase}"
            ) from exc

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

    async def _guard_redirect(self, response: httpx.Response) -> None:
        """httpx event hook: re-validate redirect targets against SSRF guard.

        httpx fires this hook for every response in the redirect chain.
        We only need to act on 3xx — final 2xx already passed pre-flight
        validation. Raise ReadURLError to abort the chain.
        """
        if response.is_redirect:
            location = response.headers.get("location")
            if location:
                target = httpx.URL(response.url).join(location)
                _validate_url(str(target))
