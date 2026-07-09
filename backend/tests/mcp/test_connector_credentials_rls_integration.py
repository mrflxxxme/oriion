"""Integration: mcp.connector_credentials RLS isolation + migration up/down.

Requires a real Postgres (testcontainers or TEST_DATABASE_URL) with all
migrations applied — the session-scoped ``_bootstrap_db`` fixture in
``tests/conftest.py`` runs ``alembic upgrade heads`` (which includes
``mcp/0002_connector_credentials``). Deselected by default addopts
(``-m "not integration"``); runs in CI's integration job / on the stack.

Covers:
  * Workspace-A credential is NOT visible to workspace-B under RLS.
  * FORCE ROW LEVEL SECURITY + the workspace-isolation policy exist (pure-CREATE
    RLS from scratch).
  * ``alembic downgrade`` (drops the table) then ``upgrade`` (recreates it) —
    the migration is reversible and its downgrade is a clean DROP.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_force_rls_and_policy_present(db_session: AsyncSession) -> None:
    """The migration enabled+forced RLS and created the workspace-isolation policy."""
    res = await db_session.execute(
        text(
            "SELECT relrowsecurity, relforcerowsecurity "
            "FROM pg_class WHERE oid = 'mcp.connector_credentials'::regclass"
        )
    )
    assert res.first() == (True, True)

    policies = await db_session.execute(
        text(
            "SELECT polname FROM pg_policy "
            "WHERE polrelid = 'mcp.connector_credentials'::regclass"
        )
    )
    names = {r[0] for r in policies.all()}
    assert "connector_credentials_workspace_isolation" in names


@pytest.mark.asyncio
async def test_credentials_isolated_by_rls(db_session: AsyncSession) -> None:
    """Workspace A cannot see workspace B's connector credential via RLS."""
    ws_a, ws_b = uuid4(), uuid4()
    user_a, user_b = uuid4(), uuid4()
    cell_a = uuid4()

    for ws in (ws_a, ws_b):
        await db_session.execute(
            text(
                "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
                "VALUES (:id, :slug, :name)"
            ),
            {"id": str(ws), "slug": f"ws-{ws}", "name": "W"},
        )

    # Insert with RLS bypassed (the migration/test session is superuser).
    await db_session.execute(
        text(
            "INSERT INTO mcp.connector_credentials "
            "(workspace_id, connector_slug, cred_encrypted, cred_fingerprint, label, created_by) "
            "VALUES (:ws, 'telegram-bot', :enc, 'aaaa1111', 'main', :by)"
        ),
        {"ws": str(ws_a), "enc": b"\x00\x01A", "by": str(user_a)},
    )
    await db_session.execute(
        text(
            "INSERT INTO mcp.connector_credentials "
            "(workspace_id, connector_slug, cred_encrypted, cred_fingerprint, label, created_by) "
            "VALUES (:ws, 'telegram-bot', :enc, 'bbbb2222', 'main', :by)"
        ),
        {"ws": str(ws_b), "enc": b"\x00\x01B", "by": str(user_b)},
    )

    # As workspace A (drop to the non-superuser app role so RLS applies).
    async with set_tenant_context(db_session, workspace_id=ws_a, cell_id=cell_a, user_id=user_a):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        result = await db_session.execute(
            text("SELECT workspace_id FROM mcp.connector_credentials")
        )
        visible = {str(r[0]) for r in result.all()}

    assert str(ws_a) in visible
    assert str(ws_b) not in visible, "RLS leak: workspace B credential visible to workspace A"


def _table_exists(sync_url: str, qualified: str) -> bool:
    import psycopg

    with psycopg.connect(sync_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (qualified,))
        row = cur.fetchone()
        return row is not None and row[0] is not None


def test_migration_downgrade_upgrade_round_trip(test_db_url: str) -> None:
    """downgrade drops mcp.connector_credentials; upgrade recreates it (reversible)."""
    from alembic import command
    from alembic.config import Config

    sync_url = test_db_url.replace("+asyncpg", "")
    async_url = (
        test_db_url
        if "+asyncpg" in test_db_url
        else test_db_url.replace("postgresql://", "postgresql+asyncpg://")
    )

    backend_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "migrations"))

    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = async_url
    try:
        # Precondition: bootstrap left the table present.
        assert _table_exists(sync_url, "mcp.connector_credentials")

        # downgrade() — pure DROP of the new table only.
        command.downgrade(cfg, "mcp_0001_mcp_connections")
        assert not _table_exists(sync_url, "mcp.connector_credentials")

        # upgrade() back to heads — recreates the table for the rest of the suite.
        command.upgrade(cfg, "heads")
        assert _table_exists(sync_url, "mcp.connector_credentials")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev
