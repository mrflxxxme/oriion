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
from src.runtime.connectors_runner import build_connector_tools
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


def _build(session: Any, *, audit: Any = None, telegram_transport: Any = None) -> dict[str, Any]:
    return build_connector_tools(
        session=session,
        workspace_id=uuid4(),
        task_id=uuid4(),
        cell_id=uuid4(),
        kms=LocalAESKMS(master_key=_MASTER_KEY),
        audit_sink=audit,
        telegram_transport=telegram_transport,
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
