"""Unit: connectors_runner — NativeTool closures + credential resolution + gate.

Covers the runner layer (mirrors web_search_runner): the built candidate map has
the read/draft tools and NO send_* (deny-until-01.12); a workspace with no
credential degrades gracefully; a PII arg is refused + DLP-block audited; a
successful external read is audited; and the candidate map flows through the
capability gate scoped per archetype (registrable + gated — AC-01.9b.3/.4).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.llm_gateway.exceptions import KMSError
from src.llm_gateway.services.kms_provider import LocalAESKMS
from src.mcp.models import ConnectorCredential
from src.mcp.tools.connectors.base import HttpResponse
from src.mcp.tools.connectors.exceptions import ConnectorError
from src.mcp.tools.connectors.imap_smtp import ImapMessage
from src.runtime.connectors_runner import (
    DLP_BLOCK_ACTION,
    EXTERNAL_CALL_ACTION,
    EmitConnectorAuditSink,
    build_connector_tools,
)
from src.runtime.tool_gating import gate_agent_tools
from structlog.testing import capture_logs

_MASTER_KEY = bytes(range(32))
_INN_CTX = "ИНН поставщика 7830002293"
# Obviously-fake, too-short-to-match-gitleaks Telegram bot token.
_TG_TOKEN = "123456:AA-secret"

_UPDATES = {
    "ok": True,
    "result": [{"channel_post": {"chat": {"title": "Канал"}, "text": "пост", "date": 1}}],
}


class _CredSession:
    """Fake AsyncSession serving the same row to list + get credential queries."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    async def execute(self, _stmt: Any) -> Any:
        result = MagicMock()
        result.scalars.return_value.all.return_value = self._rows
        result.scalar_one_or_none.return_value = self._rows[0] if self._rows else None
        return result


class _FakeHttp:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[str] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        self.calls.append(url)
        return HttpResponse(200, json.dumps(self.payload).encode("utf-8"))


class _FakeAudit:
    def __init__(self) -> None:
        self.external: list[tuple[str, str, str]] = []
        self.blocks: list[tuple[str, str, tuple[str, ...]]] = []

    async def record_external_call(
        self, *, connector_slug: str, tool_name: str, agent_id: str, outcome: str
    ) -> None:
        self.external.append((connector_slug, tool_name, outcome))

    async def record_dlp_block(
        self, *, connector_slug: str, tool_name: str, agent_id: str, categories: tuple[str, ...]
    ) -> None:
        self.blocks.append((connector_slug, tool_name, categories))


async def _make_cred_row(slug: str, secret: str) -> ConnectorCredential:
    kms = LocalAESKMS(master_key=_MASTER_KEY)
    row = ConnectorCredential(
        workspace_id=uuid4(),
        connector_slug=slug,
        cred_encrypted=await kms.encrypt(secret.encode("utf-8")),
        cred_fingerprint="aaaa1111",
        label="main",
        created_by=uuid4(),
    )
    row.id = uuid4()
    return row


def _build(
    session: Any,
    *,
    audit: Any = None,
    telegram_transport: Any = None,
    yandex_transport: Any = None,
    imap_transport: Any = None,
) -> dict[str, Any]:
    return build_connector_tools(
        session=session,
        workspace_id=uuid4(),
        task_id=uuid4(),
        cell_id=uuid4(),
        kms=LocalAESKMS(master_key=_MASTER_KEY),
        audit_sink=audit,
        telegram_transport=telegram_transport,
        yandex_transport=yandex_transport,
        imap_transport=imap_transport,
    )


def test_candidate_map_has_read_draft_but_no_send() -> None:
    tools = _build(_CredSession([]))
    assert set(tools) == {
        "telegram_read_updates",
        "telegram_draft_message",
        "yandex_disk_list",
        "yandex_disk_read_file",
        "yandex_disk_draft",
        "imap_read_inbox",
        "email_draft",
    }
    assert "send_telegram" not in tools
    assert "send_email" not in tools


@pytest.mark.asyncio
async def test_missing_credential_degrades_to_not_configured() -> None:
    tools = _build(_CredSession([]))
    out = await tools["telegram_read_updates"]("")
    assert "не настроен" in out


@pytest.mark.asyncio
async def test_pii_arg_refused_and_dlp_block_audited() -> None:
    audit = _FakeAudit()
    tools = _build(_CredSession([]), audit=audit)
    out = await tools["telegram_read_updates"](_INN_CTX)
    assert "DLP" in out
    assert audit.blocks and audit.blocks[0][0] == "telegram-bot"
    assert audit.blocks[0][2] == ("inn",)


@pytest.mark.asyncio
async def test_successful_read_formats_and_audits_external_call() -> None:
    audit = _FakeAudit()
    row = await _make_cred_row("telegram-bot", "bot-token")
    transport = _FakeHttp(_UPDATES)
    tools = _build(_CredSession([row]), audit=audit, telegram_transport=transport)
    out = await tools["telegram_read_updates"]("")
    assert "Канал" in out and "пост" in out
    assert transport.calls and "bot-token/getUpdates" in transport.calls[0]
    assert audit.external == [("telegram-bot", "telegram_read_updates", "success")]


@pytest.mark.asyncio
async def test_gate_scopes_connector_tools_per_archetype() -> None:
    tools = _build(_CredSession([]))
    # Archetype that lists the connector read tool → it registers.
    allowed = await gate_agent_tools(
        tools, tools_allowed=["telegram_read_updates"], agent_slug="tg_vertical"
    )
    assert set(allowed) == {"telegram_read_updates"}
    # Archetype that does not list it → denied (not attached).
    denied = await gate_agent_tools(
        tools, tools_allowed=["web_search"], agent_slug="other_vertical"
    )
    assert "telegram_read_updates" not in denied


class _TamperKMS:
    """KMS whose decrypt always fails (tampered ciphertext → InvalidTag)."""

    async def encrypt(self, plaintext: bytes) -> bytes:
        return b"tampered"

    async def decrypt(self, ciphertext: bytes) -> bytes:
        raise KMSError("AES-GCM authentication failed — ciphertext tampered")


class _TokenLeakingHttp:
    """Transport that raises a ConnectorError whose message echoes the bot token
    (simulating an un-redacted upstream) so the degrade-log scrub is exercised."""

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        raise ConnectorError(
            f"network error: cannot connect to https://api.telegram.org/bot{_TG_TOKEN}/getUpdates"
        )


@pytest.mark.asyncio
async def test_kms_error_degrades_instead_of_crashing() -> None:
    # A tampered credential (KMSError, NOT an MCPError) must degrade, not crash.
    row = await _make_cred_row("telegram-bot", "bot-token")
    tools = build_connector_tools(
        session=_CredSession([row]),  # type: ignore[arg-type]
        workspace_id=uuid4(),
        task_id=uuid4(),
        cell_id=uuid4(),
        kms=_TamperKMS(),  # type: ignore[arg-type]
        telegram_transport=_FakeHttp(_UPDATES),
    )
    out = await tools["telegram_read_updates"]("")
    assert "не настроен" in out  # safe degradation, no plaintext, no exception


@pytest.mark.asyncio
async def test_degraded_log_does_not_leak_bot_token() -> None:
    row = await _make_cred_row("telegram-bot", "bot-token")
    tools = _build(_CredSession([row]), telegram_transport=_TokenLeakingHttp())
    with capture_logs() as logs:
        out = await tools["telegram_read_updates"]("")
    assert out == ""  # generic transport error → empty degrade
    serialised = json.dumps(logs, ensure_ascii=False, default=str)
    assert _TG_TOKEN not in serialised
    assert any("/bot<redacted>/" in str(entry.get("error", "")) for entry in logs)


# --------------------------------------------------------------------------
# Additional coverage — empty-result formatting, draft closures, the
# yandex-disk + imap-smtp read/draft tool bodies, and the real
# EmitConnectorAuditSink payload shape (D7 heal cycle-2: connectors_runner.py
# was only 61% covered — every closure below was previously untested).
# --------------------------------------------------------------------------


class _FakeYandexTransport:
    """Dispatches by URL suffix: folder listing, download-href lookup, or the
    signed-href body fetch (no auth header on that last hop, per the connector).

    ``fail_on_href`` simulates the signed-href body fetch itself failing
    (network error downloading the file after a valid href was obtained).
    """

    def __init__(
        self,
        *,
        list_payload: Any = None,
        download_href: str = "",
        file_body: bytes = b"",
        fail_on_href: bool = False,
    ) -> None:
        self.list_payload = list_payload
        self.download_href = download_href
        self.file_body = file_body
        self.fail_on_href = fail_on_href
        self.calls: list[str] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        self.calls.append(url)
        if url.endswith("/resources/download"):
            return HttpResponse(200, json.dumps({"href": self.download_href}).encode("utf-8"))
        if url.endswith("/resources"):
            return HttpResponse(200, json.dumps(self.list_payload).encode("utf-8"))
        if self.fail_on_href:
            raise ConnectorError("network error: cannot connect to signed href")
        return HttpResponse(200, self.file_body)  # the signed href itself


class _FakeImapTransport:
    """Fake ``ImapTransport`` — records the call args, returns canned messages."""

    def __init__(self, messages: list[ImapMessage]) -> None:
        self.messages = messages
        self.calls: list[tuple[str, str, int]] = []

    async def fetch_inbox(self, *, credential: str, mailbox: str, limit: int) -> list[ImapMessage]:
        self.calls.append((credential, mailbox, limit))
        return self.messages


class _FailingImapTransport:
    """Fake ``ImapTransport`` that always raises a generic ``ConnectorError``."""

    async def fetch_inbox(self, *, credential: str, mailbox: str, limit: int) -> list[ImapMessage]:
        raise ConnectorError("imap network error: connection refused")


@pytest.mark.asyncio
async def test_telegram_read_updates_empty_result_formats_no_messages() -> None:
    row = await _make_cred_row("telegram-bot", "bot-token")
    transport = _FakeHttp({"ok": True, "result": []})
    tools = _build(_CredSession([row]), audit=_FakeAudit(), telegram_transport=transport)
    out = await tools["telegram_read_updates"]("")
    assert out == "Сообщений не найдено."


@pytest.mark.asyncio
async def test_telegram_draft_message_returns_stripped_text_no_credential_needed() -> None:
    tools = _build(_CredSession([]))
    out = await tools["telegram_draft_message"]("  hello draft  ")
    assert out == "hello draft"


@pytest.mark.asyncio
async def test_telegram_draft_message_pii_refused_and_dlp_block_audited() -> None:
    audit = _FakeAudit()
    tools = _build(_CredSession([]), audit=audit)
    out = await tools["telegram_draft_message"](_INN_CTX)
    assert "DLP" in out
    assert audit.blocks and audit.blocks[0][:2] == ("telegram-bot", "telegram_draft_message")


@pytest.mark.asyncio
async def test_yandex_disk_list_formats_items_and_audits_external_call() -> None:
    audit = _FakeAudit()
    # A non-matching row precedes the real one so credential resolution walks
    # past a miss before matching (covers the loop-continue branch too).
    other = await _make_cred_row("imap-smtp", "unrelated")
    row = await _make_cred_row("yandex-disk", "oauth-token")
    payload = {
        "_embedded": {
            "items": [
                {"name": "report.docx", "path": "/docs/report.docx", "type": "file", "size": 1024}
            ]
        }
    }
    transport = _FakeYandexTransport(list_payload=payload)
    tools = _build(_CredSession([other, row]), audit=audit, yandex_transport=transport)
    out = await tools["yandex_disk_list"]("/docs")
    assert "report.docx" in out and "/docs/report.docx" in out
    assert transport.calls and transport.calls[0].endswith("/resources")
    assert audit.external == [("yandex-disk", "yandex_disk_list", "success")]


@pytest.mark.asyncio
async def test_yandex_disk_list_empty_folder_message() -> None:
    row = await _make_cred_row("yandex-disk", "oauth-token")
    transport = _FakeYandexTransport(list_payload={"_embedded": {"items": []}})
    tools = _build(_CredSession([row]), audit=_FakeAudit(), yandex_transport=transport)
    out = await tools["yandex_disk_list"]("/empty")
    assert out == "Папка пуста или не найдена."


@pytest.mark.asyncio
async def test_yandex_disk_list_pii_path_refused_and_dlp_block_audited() -> None:
    audit = _FakeAudit()
    tools = _build(_CredSession([]), audit=audit)
    out = await tools["yandex_disk_list"](_INN_CTX)
    assert "DLP" in out
    assert audit.blocks and audit.blocks[0][:2] == ("yandex-disk", "yandex_disk_list")


@pytest.mark.asyncio
async def test_yandex_disk_read_file_success_fetches_signed_href_and_audits() -> None:
    audit = _FakeAudit()
    row = await _make_cred_row("yandex-disk", "oauth-token")
    transport = _FakeYandexTransport(
        download_href="https://downloader.disk.yandex.net/signed/abc", file_body=b"file contents"
    )
    tools = _build(_CredSession([row]), audit=audit, yandex_transport=transport)
    out = await tools["yandex_disk_read_file"]("/docs/report.docx")
    assert out == "file contents"
    assert transport.calls[0].endswith("/resources/download")
    assert transport.calls[1] == "https://downloader.disk.yandex.net/signed/abc"
    assert audit.external == [("yandex-disk", "yandex_disk_read_file", "success")]


@pytest.mark.asyncio
async def test_yandex_disk_read_file_transport_error_degrades_to_empty() -> None:
    row = await _make_cred_row("yandex-disk", "oauth-token")
    transport = _FakeYandexTransport(
        download_href="https://downloader.disk.yandex.net/signed/abc", fail_on_href=True
    )
    tools = _build(_CredSession([row]), audit=_FakeAudit(), yandex_transport=transport)
    out = await tools["yandex_disk_read_file"]("/docs/report.docx")
    assert out == ""  # generic transport error → empty degrade, never a crash


@pytest.mark.asyncio
async def test_yandex_disk_draft_returns_stripped_text_no_credential_needed() -> None:
    tools = _build(_CredSession([]))
    out = await tools["yandex_disk_draft"]("  draft content  ")
    assert out == "draft content"


@pytest.mark.asyncio
async def test_yandex_disk_draft_pii_refused_and_dlp_block_audited() -> None:
    audit = _FakeAudit()
    tools = _build(_CredSession([]), audit=audit)
    out = await tools["yandex_disk_draft"](_INN_CTX)
    assert "DLP" in out
    assert audit.blocks and audit.blocks[0][:2] == ("yandex-disk", "yandex_disk_draft")


@pytest.mark.asyncio
async def test_imap_read_inbox_formats_messages_and_audits_external_call() -> None:
    audit = _FakeAudit()
    row = await _make_cred_row("imap-smtp", '{"host": "imap.example.com"}')
    messages = [ImapMessage(sender="a@b.com", subject="Привет", snippet="текст письма", date="")]
    transport = _FakeImapTransport(messages)
    tools = _build(_CredSession([row]), audit=audit, imap_transport=transport)
    out = await tools["imap_read_inbox"]("")
    assert "a@b.com" in out and "Привет" in out and "текст письма" in out
    assert transport.calls == [('{"host": "imap.example.com"}', "INBOX", 20)]
    assert audit.external == [("imap-smtp", "imap_read_inbox", "success")]


@pytest.mark.asyncio
async def test_imap_read_inbox_empty_mailbox_message() -> None:
    row = await _make_cred_row("imap-smtp", '{"host": "imap.example.com"}')
    tools = _build(_CredSession([row]), audit=_FakeAudit(), imap_transport=_FakeImapTransport([]))
    out = await tools["imap_read_inbox"]("INBOX")
    assert out == "Входящих сообщений не найдено."


@pytest.mark.asyncio
async def test_imap_read_inbox_transport_error_degrades_to_empty() -> None:
    row = await _make_cred_row("imap-smtp", '{"host": "imap.example.com"}')
    tools = _build(_CredSession([row]), audit=_FakeAudit(), imap_transport=_FailingImapTransport())
    out = await tools["imap_read_inbox"]("INBOX")
    assert out == ""  # generic transport error → empty degrade, never a crash


@pytest.mark.asyncio
async def test_email_draft_returns_stripped_text_no_credential_needed() -> None:
    tools = _build(_CredSession([]))
    out = await tools["email_draft"]("  dear customer  ")
    assert out == "dear customer"


@pytest.mark.asyncio
async def test_email_draft_pii_refused_and_dlp_block_audited() -> None:
    audit = _FakeAudit()
    tools = _build(_CredSession([]), audit=audit)
    out = await tools["email_draft"](_INN_CTX)
    assert "DLP" in out
    assert audit.blocks and audit.blocks[0][:2] == ("imap-smtp", "email_draft")


@pytest.mark.asyncio
async def test_emit_connector_audit_sink_record_external_call_payload_has_no_secret_or_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SECURITY: the real audit sink's INSERT payload carries only
    slug/tool/agent/outcome — never a tool argument, credential, or raw value.
    """
    captured: dict[str, Any] = {}

    async def _fake_emit_audit_event(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("src.runtime.connectors_runner.emit_audit_event", _fake_emit_audit_event)
    sink = EmitConnectorAuditSink(
        _CredSession([]), task_id=uuid4(), cell_id=uuid4(), workspace_id=uuid4()
    )
    await sink.record_external_call(
        connector_slug="telegram-bot",
        tool_name="telegram_read_updates",
        agent_id="agent-1",
        outcome="success",
    )
    assert captured["action"] == EXTERNAL_CALL_ACTION
    assert captured["actor_type"] == "system"
    assert captured["payload"] == {
        "connector_slug": "telegram-bot",
        "tool_name": "telegram_read_updates",
        "agent_id": "agent-1",
        "outcome": "success",
    }


@pytest.mark.asyncio
async def test_emit_connector_audit_sink_record_dlp_block_payload_has_no_secret_or_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def _fake_emit_audit_event(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("src.runtime.connectors_runner.emit_audit_event", _fake_emit_audit_event)
    sink = EmitConnectorAuditSink(
        _CredSession([]), task_id=uuid4(), cell_id=uuid4(), workspace_id=uuid4()
    )
    await sink.record_dlp_block(
        connector_slug="imap-smtp",
        tool_name="imap_read_inbox",
        agent_id="agent-2",
        categories=("inn", "snils"),
    )
    assert captured["action"] == DLP_BLOCK_ACTION
    assert captured["payload"] == {
        "connector_slug": "imap-smtp",
        "tool_name": "imap_read_inbox",
        "agent_id": "agent-2",
        "categories": ["inn", "snils"],
    }
