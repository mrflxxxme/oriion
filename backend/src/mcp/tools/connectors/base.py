"""Shared connector substrate — transport, audit ports, base cross-cutting logic.

Every Wave-1 connector (telegram-bot / yandex-disk / imap-smtp) mirrors the
``WebSearchTool`` / ``ReadURLTool`` pattern (ADR-041): async, rate-limited, typed
``MCPError`` subclasses, degrade gracefully. This module factors the pieces they
all share:

* ``HttpTransport`` — an INJECTABLE transport Protocol so tests drive the
  connectors with a mock (``httpx.MockTransport``) and no live network. The real
  ``HttpxTransport`` streams with a hard body-size cap (mirrors web_search's
  ``_get_capped``) so a hostile/buggy upstream can't OOM the worker.
* ``ConnectorAuditSink`` — the per-external-call + DLP-block audit port (AC-7).
  Default no-op for pure unit construction; the runner wires the real emitter.
* ``BaseConnector`` — the ordered per-call pipeline the connectors reuse:
  rate-limit → DLP-screen outgoing args (exfil guard) → (credential) → transport
  → audit. The DLP screen runs BEFORE any external call, unconditionally.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Protocol

import httpx
import structlog

from src.mcp.exceptions import ToolRateLimitExceeded
from src.mcp.tools.connectors.dlp_screen import (
    ConnectorDlpScreen,
    default_connector_dlp_screen,
)
from src.mcp.tools.connectors.exceptions import ConnectorError, ConnectorNotConfigured
from src.mcp.tools.rate_limit import ToolRateLimiter

logger = structlog.get_logger(__name__)

# Secret-in-URL / secret-in-header hygiene (SECURE audit 01.9b). A transport
# error's ``str()`` can echo the request URL (the Telegram bot token lives in the
# path: ``/bot<token>/…``) or an auth header value. ``redact_secrets`` scrubs
# credential material from any error string BEFORE it reaches a ConnectorError
# message or a log line, so no connector's error path can emit a secret. Patterns
# are linear (bounded, no backtracking) — ReDoS-safe.
_SECRET_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    # Telegram Bot-API token embedded in the URL path: /bot<id>:<hash>/method
    (re.compile(r"/bot[^/\s]+"), "/bot<redacted>"),
    # ``token=<value>`` query params (any connector).
    (re.compile(r"(?i)(token=)[^&\s]+"), r"\1<redacted>"),
    # Authorization scheme values: ``OAuth <t>`` / ``Api-Key <t>`` / ``Bearer <t>``.
    (re.compile(r"(?i)\b(OAuth|Api-Key|Bearer)\s+\S+"), r"\1 <redacted>"),
)


def redact_secrets(text: str) -> str:
    """Scrub credential material (bot token, OAuth/Api-Key/Bearer, ``token=``).

    Applied to every transport-error string a connector wraps or logs so a
    URL-bearing exception can never leak a secret. Idempotent + safe on clean text.
    """
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


_DEFAULT_TIMEOUT_SECONDS: Final = 8.0
# Cap the connector response body (mirrors web_search / read_url): a compromised,
# spoofed or buggy upstream could otherwise stream an unbounded body and OOM the
# single worker before parsing trims it.
_MAX_BODY_BYTES: Final = 5 * 1024 * 1024
_DEFAULT_LIMIT_PER_MIN: Final = 20
_WINDOW_SECONDS: Final = 60


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Transport-neutral HTTP response — status + already-capped body bytes."""

    status_code: int
    body: bytes

    def json(self) -> Any:
        """Parse the body as JSON (raises ``ValueError`` on non-JSON)."""
        import json

        return json.loads(self.body)

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")


class HttpTransport(Protocol):
    """Injectable HTTP transport — real ``HttpxTransport`` or a test mock."""

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> HttpResponse: ...


class HttpxTransport:
    """Real httpx-backed transport with a hard body-size cap.

    ``transport`` (an ``httpx.AsyncBaseTransport``) is injectable so a test can
    drive the REAL streaming/cap/error-mapping path with ``httpx.MockTransport``
    — no live network. Production leaves it ``None`` (a normal AsyncClient).
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_body_bytes: int = _MAX_BODY_BYTES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_body_bytes = max_body_bytes
        self._transport = transport

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> HttpResponse:
        client_kwargs: dict[str, Any] = {"timeout": httpx.Timeout(self._timeout_seconds)}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        try:
            async with (
                httpx.AsyncClient(**client_kwargs) as client,
                client.stream(
                    method,
                    url,
                    headers=dict(headers) if headers else None,
                    params=dict(params) if params else None,
                    json=dict(json_body) if json_body else None,
                ) as response,
            ):
                response.raise_for_status()
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > self._max_body_bytes:
                        raise ConnectorError(
                            f"connector response exceeded {self._max_body_bytes} bytes cap"
                        )
                    chunks.append(chunk)
                return HttpResponse(status_code=response.status_code, body=b"".join(chunks))
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(f"http error: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            # SECURITY: scrub any credential material (bot token / auth header) the
            # error string may echo from the request URL before it surfaces.
            raise ConnectorError(f"network error: {redact_secrets(str(exc))}") from exc


class ConnectorAuditSink(Protocol):
    """Audit sink for connector external calls + DLP blocks (AC-01.9b.7).

    SECURITY: the impl MUST receive only non-secret metadata — connector slug,
    tool name, agent id, outcome / category labels — never a tool argument, the
    credential, or a raw PII value.
    """

    async def record_external_call(
        self, *, connector_slug: str, tool_name: str, agent_id: str, outcome: str
    ) -> None: ...

    async def record_dlp_block(
        self,
        *,
        connector_slug: str,
        tool_name: str,
        agent_id: str,
        categories: tuple[str, ...],
    ) -> None: ...


class NoopConnectorAuditSink:
    """Default no-op sink (pure unit construction / no DB session in scope)."""

    async def record_external_call(
        self, *, connector_slug: str, tool_name: str, agent_id: str, outcome: str
    ) -> None:
        del connector_slug, tool_name, agent_id, outcome

    async def record_dlp_block(
        self, *, connector_slug: str, tool_name: str, agent_id: str, categories: tuple[str, ...]
    ) -> None:
        del connector_slug, tool_name, agent_id, categories


class BaseConnector:
    """Shared per-call pipeline for the Wave-1 connectors.

    Ordering (per tool call):
      1. rate-limit (per agent_id + tool_name) — defends against agent loops;
      2. DLP-screen the outgoing args — the exfil guard; raises before any
         external call so PII can never leave via a tool argument;
      3. (external tools) require the credential — missing → graceful
         ``ConnectorNotConfigured`` degrade, never a crash;
      4. transport call + parse (subclass);
      5. audit the external call (AC-7) — external tools only.
    """

    def __init__(
        self,
        *,
        connector_slug: str,
        credential: str | None,
        rate_limiter: ToolRateLimiter | None = None,
        limit_per_min: int = _DEFAULT_LIMIT_PER_MIN,
        dlp_screen: ConnectorDlpScreen = default_connector_dlp_screen,
        audit_sink: ConnectorAuditSink | None = None,
    ) -> None:
        self._connector_slug = connector_slug
        self._credential = credential
        self._rate_limiter = rate_limiter
        self._limit_per_min = limit_per_min
        self._dlp_screen = dlp_screen
        self._audit_sink: ConnectorAuditSink = audit_sink or NoopConnectorAuditSink()

    def _require_credential(self) -> str:
        if not self._credential:
            raise ConnectorNotConfigured(
                f"connector {self._connector_slug!r} has no credential configured"
            )
        return self._credential

    async def _rate_limit(self, agent_id: str, tool_name: str) -> None:
        if self._rate_limiter is None:
            return
        verdict = await self._rate_limiter.check_detailed(
            agent_id=agent_id,
            tool_name=tool_name,
            limit=self._limit_per_min,
            window_seconds=_WINDOW_SECONDS,
        )
        if not verdict.allowed:
            raise ToolRateLimitExceeded(
                retry_after=verdict.retry_after,
                detail=f"{tool_name} limit {self._limit_per_min}/min exceeded",
            )

    async def _screen(self, tool_name: str, args: list[str]) -> None:
        """Run the outgoing-args DLP screen (raises ``ConnectorDlpBlocked``)."""
        await self._dlp_screen.screen(
            args, connector_slug=self._connector_slug, tool_name=tool_name
        )

    async def _audit_external(
        self, tool_name: str, agent_id: str, *, outcome: str = "success"
    ) -> None:
        await self._audit_sink.record_external_call(
            connector_slug=self._connector_slug,
            tool_name=tool_name,
            agent_id=agent_id,
            outcome=outcome,
        )


__all__ = [
    "BaseConnector",
    "ConnectorAuditSink",
    "HttpResponse",
    "HttpTransport",
    "HttpxTransport",
    "NoopConnectorAuditSink",
    "redact_secrets",
]
