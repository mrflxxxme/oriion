"""Unit: imap-smtp connector — inbox READ over a MOCK transport + DLP/rate/send.

Covers AC-01.9b.1 (inbox parses / draft returns), .2 (DLP blocks PII args before
the external call), .4 (send_email is DANGEROUS + guarded), .7 (external call
audited), no-cred degrade, and rate limiting — NO live IMAP / creds.
"""

from __future__ import annotations

import pytest
from src.mcp.exceptions import ToolRateLimitExceeded
from src.mcp.tools.connectors.exceptions import (
    ConnectorDlpBlocked,
    ConnectorNotConfigured,
    ConnectorSendDisabled,
)
from src.mcp.tools.connectors.imap_smtp import ImapMessage, ImapSmtpConnector
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.security.capability import requires_approval

_INN_CTX = "ИНН 7830002293"  # valid ИНН-10 with labelling token (synthetic)

_MESSAGES = [
    ImapMessage(sender="a@corp.test", subject="Отчёт", snippet="тело письма", date="Mon"),
    ImapMessage(sender="b@corp.test", subject="Счёт", snippet="ещё тело", date="Tue"),
]


class _FakeImap:
    """Mock ``ImapTransport`` — records calls, returns canned messages."""

    def __init__(self, messages: list[ImapMessage]) -> None:
        self.messages = messages
        self.calls: list[tuple[str, str, int]] = []

    async def fetch_inbox(self, *, credential: str, mailbox: str, limit: int) -> list[ImapMessage]:
        self.calls.append((credential, mailbox, limit))
        return self.messages


class _FakeAudit:
    def __init__(self) -> None:
        self.external: list[tuple[str, str, str]] = []

    async def record_external_call(
        self, *, connector_slug: str, tool_name: str, agent_id: str, outcome: str
    ) -> None:
        self.external.append((connector_slug, tool_name, outcome))

    async def record_dlp_block(
        self, *, connector_slug: str, tool_name: str, agent_id: str, categories: tuple[str, ...]
    ) -> None:  # pragma: no cover - not exercised here
        return None


_CRED = '{"host":"imap.test","port":993,"username":"u","password":"p"}'


@pytest.mark.asyncio
async def test_read_inbox_returns_messages() -> None:
    tr = _FakeImap(_MESSAGES)
    conn = ImapSmtpConnector(credential=_CRED, transport=tr)
    msgs = await conn.read_inbox("INBOX", agent_id="agent-1")
    assert [m.subject for m in msgs] == ["Отчёт", "Счёт"]
    assert tr.calls == [(_CRED, "INBOX", 20)]


@pytest.mark.asyncio
async def test_draft_email_returns_text() -> None:
    conn = ImapSmtpConnector(credential=None, transport=_FakeImap([]))
    out = await conn.draft_email("  тело черновика  ", agent_id="agent-1")
    assert out == "тело черновика"


@pytest.mark.asyncio
async def test_missing_credential_degrades() -> None:
    conn = ImapSmtpConnector(credential=None, transport=_FakeImap(_MESSAGES))
    with pytest.raises(ConnectorNotConfigured):
        await conn.read_inbox("INBOX", agent_id="agent-1")


@pytest.mark.asyncio
async def test_dlp_blocks_mailbox_arg_with_pii() -> None:
    tr = _FakeImap(_MESSAGES)
    conn = ImapSmtpConnector(credential=_CRED, transport=tr)
    with pytest.raises(ConnectorDlpBlocked) as ei:
        await conn.read_inbox(_INN_CTX, agent_id="agent-1")
    assert "inn" in ei.value.categories
    assert tr.calls == []


@pytest.mark.asyncio
async def test_dlp_blocks_draft_with_pii() -> None:
    conn = ImapSmtpConnector(credential=None, transport=_FakeImap([]))
    with pytest.raises(ConnectorDlpBlocked):
        await conn.draft_email(f"Здравствуйте, {_INN_CTX}", agent_id="agent-1")


@pytest.mark.asyncio
async def test_external_call_audited() -> None:
    audit = _FakeAudit()
    conn = ImapSmtpConnector(credential=_CRED, transport=_FakeImap(_MESSAGES), audit_sink=audit)
    await conn.read_inbox("INBOX", agent_id="agent-1")
    assert audit.external == [("imap-smtp", "imap_read_inbox", "success")]


@pytest.mark.asyncio
async def test_rate_limit_enforced(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    conn = ImapSmtpConnector(
        credential=_CRED, transport=_FakeImap(_MESSAGES), rate_limiter=limiter, limit_per_min=1
    )
    await conn.read_inbox("INBOX", agent_id="agent-1")
    with pytest.raises(ToolRateLimitExceeded):
        await conn.read_inbox("INBOX", agent_id="agent-1")


@pytest.mark.asyncio
async def test_send_is_guarded_stub_and_dangerous() -> None:
    conn = ImapSmtpConnector(credential=_CRED, transport=_FakeImap(_MESSAGES))
    with pytest.raises(ConnectorSendDisabled):
        await conn.send("outbound", agent_id="agent-1")
    assert requires_approval("send_email") is True
