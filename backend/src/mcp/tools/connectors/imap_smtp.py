"""imap-smtp connector — IMAP inbox READ + email DRAFT (Phase 01.9b, ADR-041).

Read = fetch recent inbox messages via IMAP. Draft = prepare an email body for an
artifact (no external call, no credential). Send = guarded DANGEROUS stub
(deny-until-approval-UI 01.12) — never performs a real SMTP send.

The IMAP transport is injectable (``ImapTransport``) so unit tests drive it with a
mock and NO live network / creds. The real ``ImaplibTransport`` (stdlib
``imaplib.IMAP4_SSL`` in a worker thread) is used only when a credential is
configured (deferred live-smoke, DV-11). The credential is an opaque UTF-8 string
that the connector-credential custody layer stores verbatim; pass B serialises the
IMAP host/user/password as JSON upstream.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Final, Protocol

from src.mcp.tools.connectors.base import BaseConnector
from src.mcp.tools.connectors.exceptions import ConnectorError, ConnectorSendDisabled

SLUG: Final = "imap-smtp"
TOOL_READ_INBOX: Final = "imap_read_inbox"
TOOL_DRAFT: Final = "email_draft"
TOOL_SEND: Final = "send_email"

_DEFAULT_LIMIT: Final = 20
_DEFAULT_IMAP_PORT: Final = 993
_SNIPPET_CHARS: Final = 500


@dataclass(frozen=True, slots=True)
class ImapMessage:
    """One parsed inbox message (headers + a short body snippet)."""

    sender: str
    subject: str
    snippet: str
    date: str


class ImapTransport(Protocol):
    """Injectable IMAP transport — real ``ImaplibTransport`` or a test mock."""

    async def fetch_inbox(
        self, *, credential: str, mailbox: str, limit: int
    ) -> list[ImapMessage]: ...


class ImaplibTransport:
    """Real IMAP transport over stdlib ``imaplib.IMAP4_SSL`` in a worker thread.

    The blocking imaplib calls run via ``asyncio.to_thread`` so the connector's
    async surface stays non-blocking. Exercised only against a live mailbox
    (DV-11) — unit tests use a mock transport, so the network body is
    ``# pragma: no cover``.
    """

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def fetch_inbox(self, *, credential: str, mailbox: str, limit: int) -> list[ImapMessage]:
        try:
            creds = json.loads(credential)
        except ValueError as exc:
            raise ConnectorError("imap-smtp credential is not valid JSON") from exc
        if not isinstance(creds, dict):
            raise ConnectorError("imap-smtp credential must be a JSON object")
        return await asyncio.to_thread(self._fetch_sync, creds, mailbox, limit)

    def _fetch_sync(  # pragma: no cover - needs a live IMAP server (DV-11)
        self, creds: dict[str, Any], mailbox: str, limit: int
    ) -> list[ImapMessage]:
        import email
        import imaplib
        from email.header import decode_header, make_header

        host = str(creds.get("host") or "")
        if not host:
            raise ConnectorError("imap-smtp credential missing 'host'")
        port = int(creds.get("port") or _DEFAULT_IMAP_PORT)
        username = str(creds.get("username") or "")
        password = str(creds.get("password") or "")

        out: list[ImapMessage] = []
        with imaplib.IMAP4_SSL(host=host, port=port, timeout=self._timeout_seconds) as imap:
            imap.login(username, password)
            imap.select(mailbox or "INBOX", readonly=True)
            _typ, data = imap.search(None, "ALL")
            ids = data[0].split() if data and data[0] else []
            for msg_id in reversed(ids[-limit:]):
                _t, raw = imap.fetch(msg_id, "(RFC822)")
                if not raw or not isinstance(raw[0], tuple):
                    continue
                parsed = email.message_from_bytes(raw[0][1])
                out.append(
                    ImapMessage(
                        sender=str(make_header(decode_header(parsed.get("From", "")))),
                        subject=str(make_header(decode_header(parsed.get("Subject", "")))),
                        snippet=_extract_snippet(parsed),
                        date=str(parsed.get("Date", "")),
                    )
                )
        return out


def _extract_snippet(parsed: Any) -> str:  # pragma: no cover - live IMAP path only
    """First text/plain fragment, trimmed to a bounded snippet."""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode("utf-8", errors="replace")[:_SNIPPET_CHARS]
        return ""
    payload = parsed.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode("utf-8", errors="replace")[:_SNIPPET_CHARS]
    return str(parsed.get_payload())[:_SNIPPET_CHARS]


class ImapSmtpConnector(BaseConnector):
    """IMAP/SMTP connector — read the inbox, draft an email (guarded send)."""

    def __init__(
        self,
        *,
        credential: str | None,
        transport: ImapTransport | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(connector_slug=SLUG, credential=credential, **base_kwargs)
        self._transport: ImapTransport = transport or ImaplibTransport()

    async def read_inbox(
        self, mailbox: str = "INBOX", *, agent_id: str = "system", limit: int = _DEFAULT_LIMIT
    ) -> list[ImapMessage]:
        """READ: fetch recent inbox messages via IMAP."""
        await self._rate_limit(agent_id, TOOL_READ_INBOX)
        await self._screen(TOOL_READ_INBOX, [mailbox])
        credential = self._require_credential()
        messages = await self._transport.fetch_inbox(
            credential=credential, mailbox=mailbox or "INBOX", limit=limit
        )
        await self._audit_external(TOOL_READ_INBOX, agent_id)
        return messages

    async def draft_email(self, text: str, *, agent_id: str = "system") -> str:
        """DRAFT: prepare an email body for an artifact (no external call)."""
        await self._rate_limit(agent_id, TOOL_DRAFT)
        await self._screen(TOOL_DRAFT, [text])
        return text.strip()

    async def send(self, text: str, *, agent_id: str = "system") -> str:  # noqa: ARG002
        """SEND (guarded stub): autonomous send is deny-until-approval-UI (01.12).

        Never performs a real SMTP send. Also DANGEROUS-classified, so the
        capability gate denies registration long before this is reachable.
        """
        raise ConnectorSendDisabled("send_email is disabled until the approval UI (01.12)")


__all__ = [
    "SLUG",
    "TOOL_DRAFT",
    "TOOL_READ_INBOX",
    "TOOL_SEND",
    "ImaplibTransport",
    "ImapMessage",
    "ImapSmtpConnector",
    "ImapTransport",
]
