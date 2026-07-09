"""Unit: telegram-bot connector — READ/DRAFT over a MOCK transport + DLP/rate/send.

Covers AC-01.9b.1 (read parses / draft returns), .2 (DLP blocks PII args before
the external call), .4 (send_telegram is DANGEROUS + guarded), .7 (external call
audited), graceful no-cred degrade, and per-agent rate limiting — all with NO
live network (injected mock transport).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from src.mcp.exceptions import ToolRateLimitExceeded
from src.mcp.tools.connectors.base import HttpResponse
from src.mcp.tools.connectors.exceptions import (
    ConnectorDlpBlocked,
    ConnectorNotConfigured,
    ConnectorSendDisabled,
)
from src.mcp.tools.connectors.telegram_bot import TelegramBotConnector
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.security.capability import requires_approval

# Valid ИНН-10 (checksum-OK) with an INN-labelling token → the 01.9a context gate
# flags it. Synthetic — not a real taxpayer.
_INN_CTX = "ИНН поставщика 7830002293"

_UPDATES = {
    "ok": True,
    "result": [
        {
            "update_id": 1,
            "channel_post": {"chat": {"title": "Мой канал"}, "text": "Первый пост", "date": 100},
        },
        {
            "update_id": 2,
            "message": {"chat": {"username": "grp"}, "text": "второй", "date": 200},
        },
    ],
}


class _FakeHttp:
    """Mock ``HttpTransport`` — records calls, returns a canned JSON body."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        self.calls.append((method, url, params))
        return HttpResponse(status_code=200, body=json.dumps(self.payload).encode("utf-8"))


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


@pytest.mark.asyncio
async def test_read_updates_parses_messages() -> None:
    tr = _FakeHttp(_UPDATES)
    conn = TelegramBotConnector(credential="bot-token-123", transport=tr)
    msgs = await conn.read_updates("", agent_id="agent-1")
    assert [m.chat for m in msgs] == ["Мой канал", "grp"]
    assert msgs[0].text == "Первый пост"
    # The bot token reaches the Bot-API URL path (getUpdates).
    assert "bot-token-123/getUpdates" in tr.calls[0][1]


@pytest.mark.asyncio
async def test_draft_message_returns_text() -> None:
    conn = TelegramBotConnector(credential=None, transport=_FakeHttp(_UPDATES))
    out = await conn.draft_message("  привет команде  ", agent_id="agent-1")
    assert out == "привет команде"


@pytest.mark.asyncio
async def test_missing_credential_degrades_not_crashes() -> None:
    conn = TelegramBotConnector(credential=None, transport=_FakeHttp(_UPDATES))
    with pytest.raises(ConnectorNotConfigured):
        await conn.read_updates("", agent_id="agent-1")


@pytest.mark.asyncio
async def test_dlp_blocks_read_before_external_call() -> None:
    tr = _FakeHttp(_UPDATES)
    conn = TelegramBotConnector(credential="bot-token-123", transport=tr)
    with pytest.raises(ConnectorDlpBlocked) as ei:
        await conn.read_updates(_INN_CTX, agent_id="agent-1")
    assert "inn" in ei.value.categories
    # SECURITY: the transport was NEVER called — PII cannot leave via the arg.
    assert tr.calls == []


@pytest.mark.asyncio
async def test_dlp_blocks_draft_with_pii() -> None:
    conn = TelegramBotConnector(credential=None, transport=_FakeHttp(_UPDATES))
    with pytest.raises(ConnectorDlpBlocked):
        await conn.draft_message(f"Черновик: {_INN_CTX}", agent_id="agent-1")


@pytest.mark.asyncio
async def test_external_call_is_audited(fake_redis: object) -> None:
    audit = _FakeAudit()
    conn = TelegramBotConnector(credential="t", transport=_FakeHttp(_UPDATES), audit_sink=audit)
    await conn.read_updates("", agent_id="agent-1")
    assert audit.external == [("telegram-bot", "telegram_read_updates", "success")]


@pytest.mark.asyncio
async def test_rate_limit_enforced(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    conn = TelegramBotConnector(
        credential="t", transport=_FakeHttp(_UPDATES), rate_limiter=limiter, limit_per_min=1
    )
    await conn.read_updates("", agent_id="agent-1")  # 1st: allowed
    with pytest.raises(ToolRateLimitExceeded):
        await conn.read_updates("", agent_id="agent-1")  # 2nd: over the 1/min cap


@pytest.mark.asyncio
async def test_send_is_guarded_stub_and_classified_dangerous() -> None:
    conn = TelegramBotConnector(credential="t", transport=_FakeHttp(_UPDATES))
    with pytest.raises(ConnectorSendDisabled):
        await conn.send("outbound text", agent_id="agent-1")
    # And the capability classifier keeps it DANGEROUS (gate denies registration).
    assert requires_approval("send_telegram") is True


@pytest.mark.asyncio
async def test_read_degrades_to_empty_on_not_ok_payload() -> None:
    # A hostile / malformed upstream must NOT crash — degrade to [].
    conn = TelegramBotConnector(credential="t", transport=_FakeHttp({"ok": False}))
    assert await conn.read_updates("", agent_id="agent-1") == []


@pytest.mark.asyncio
async def test_numeric_query_becomes_getupdates_offset() -> None:
    tr = _FakeHttp(_UPDATES)
    conn = TelegramBotConnector(credential="t", transport=tr)
    await conn.read_updates("42", agent_id="agent-1")
    assert tr.calls[0][2]["offset"] == 42
