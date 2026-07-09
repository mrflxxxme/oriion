"""Integration: connector runner against real PG — cred round-trip + audit row.

Requires a real Postgres with migrations applied (deselected by default via
``-m "not integration"``). Proves the runner resolves a KMS-stored credential
through ``connector_credential_service`` and writes an ``audit.audit_log`` row on
each external call (AC-01.9b.5 round-trip + AC-01.9b.7 audit) — end-to-end, with a
mock HTTP transport (no live Telegram).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.llm_gateway.services.kms_provider import LocalAESKMS
from src.mcp.services.connector_credential_service import store_credential
from src.mcp.tools.connectors.base import HttpResponse
from src.runtime.connectors_runner import (
    DLP_BLOCK_ACTION,
    EXTERNAL_CALL_ACTION,
    build_connector_tools,
)

pytestmark = pytest.mark.integration

_MASTER_KEY = bytes(range(32))
_INN_CTX = "ИНН поставщика 7830002293"
_UPDATES = {
    "ok": True,
    "result": [{"channel_post": {"chat": {"title": "Канал"}, "text": "пост", "date": 1}}],
}


class _FakeHttp:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        return HttpResponse(200, json.dumps(self.payload).encode("utf-8"))


async def _insert_workspace(db_session: AsyncSession, ws: Any) -> None:
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(ws), "slug": f"ws-{ws}", "name": "W"},
    )


@pytest.mark.asyncio
async def test_runner_resolves_credential_and_audits_external_call(
    db_session: AsyncSession,
) -> None:
    ws, user, cell, task = uuid4(), uuid4(), uuid4(), uuid4()
    await _insert_workspace(db_session, ws)
    kms = LocalAESKMS(master_key=_MASTER_KEY)
    await store_credential(
        db_session,
        kms,
        workspace_id=ws,
        connector_slug="telegram-bot",
        plaintext_secret="bot-token-xyz",
        label="main",
        created_by=user,
    )
    await db_session.flush()

    tools = build_connector_tools(
        session=db_session,
        workspace_id=ws,
        task_id=task,
        cell_id=cell,
        kms=kms,
        telegram_transport=_FakeHttp(_UPDATES),
    )
    out = await tools["telegram_read_updates"]("")
    assert "Канал" in out and "пост" in out

    res = await db_session.execute(
        text("SELECT count(*) FROM audit.audit_log WHERE action = :a AND resource_id = :r"),
        {"a": EXTERNAL_CALL_ACTION, "r": str(task)},
    )
    assert res.scalar_one() == 1


@pytest.mark.asyncio
async def test_runner_audits_dlp_block_on_pii_arg(db_session: AsyncSession) -> None:
    ws, cell, task = uuid4(), uuid4(), uuid4()
    await _insert_workspace(db_session, ws)
    tools = build_connector_tools(
        session=db_session,
        workspace_id=ws,
        task_id=task,
        cell_id=cell,
        kms=LocalAESKMS(master_key=_MASTER_KEY),
        telegram_transport=_FakeHttp(_UPDATES),
    )
    out = await tools["telegram_read_updates"](_INN_CTX)
    assert "DLP" in out

    res = await db_session.execute(
        text("SELECT count(*) FROM audit.audit_log WHERE action = :a AND resource_id = :r"),
        {"a": DLP_BLOCK_ACTION, "r": str(task)},
    )
    assert res.scalar_one() == 1
