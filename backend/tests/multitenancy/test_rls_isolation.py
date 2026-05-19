"""Integration: RLS isolation between cells.

Requires a real Postgres database via TEST_DATABASE_URL with the
multitenancy + rbac migrations applied. Skip locally if PG isn't running;
CI's integration job runs this against the docker-compose stack.

The test creates two workspaces + cells + memberships under different
users; then asserts that user A cannot SELECT user B's cell_members row
when current_user_id GUC is set to user A.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context

pytestmark = pytest.mark.integration


async def _ensure_role(session: AsyncSession, slug: str) -> str:
    """Return the role_id of a seed role by slug — assumes seed migration ran."""
    res = await session.execute(
        text("SELECT id FROM rbac.system_roles WHERE slug = :s"),
        {"s": slug},
    )
    row = res.first()
    assert row is not None, f"seed role {slug!r} missing — run migrations first"
    return str(row[0])


@pytest.mark.asyncio
async def test_cell_members_isolated_by_rls(db_session: AsyncSession) -> None:
    """User A in cell A cannot see cell B's members via RLS."""
    role_id = await _ensure_role(db_session, "owner")
    user_a, user_b = uuid4(), uuid4()
    ws_a_id, ws_b_id = uuid4(), uuid4()
    cell_a_id, cell_b_id = uuid4(), uuid4()

    # Insert with RLS bypassed (the migration session is superuser).
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(ws_a_id), "slug": f"ws-a-{ws_a_id}", "name": "WSA"},
    )
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(ws_b_id), "slug": f"ws-b-{ws_b_id}", "name": "WSB"},
    )
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'A')"
        ),
        {"id": str(cell_a_id), "ws": str(ws_a_id)},
    )
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'B')"
        ),
        {"id": str(cell_b_id), "ws": str(ws_b_id)},
    )
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.cell_members (cell_id, user_id, role_id) "
            "VALUES (:cell, :user, :role)"
        ),
        {"cell": str(cell_a_id), "user": str(user_a), "role": role_id},
    )
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.cell_members (cell_id, user_id, role_id) "
            "VALUES (:cell, :user, :role)"
        ),
        {"cell": str(cell_b_id), "user": str(user_b), "role": role_id},
    )

    # As user A — should see only cell A's members.
    #
    # Drop to the non-superuser app role for the SELECT — PostgreSQL bypasses
    # RLS for superusers even with FORCE ROW LEVEL SECURITY (the dev DB user
    # `oriion` IS superuser via POSTGRES_USER). SET LOCAL ROLE reverts
    # automatically when the outer TX rolls back at fixture teardown.
    async with set_tenant_context(
        db_session, workspace_id=ws_a_id, cell_id=cell_a_id, user_id=user_a
    ):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        result = await db_session.execute(text("SELECT user_id FROM multitenancy.cell_members"))
        visible_users = {str(r[0]) for r in result.all()}

    assert str(user_a) in visible_users
    assert str(user_b) not in visible_users, "RLS leak: cell B member visible to user A"
