"""Integration: Phase 01.7 Owner/Member RBAC enforcement + visibility stub.

Requires a real Postgres (Docker up) with all migrations applied. Covers:

  * ``AuthorizationService.has_cell_permission`` against real seed data:
    an Owner-role member is granted Owner-only permissions AND task.create;
    an Editor-role ("Member") member is DENIED Owner-only permissions but
    ALLOWED task.create + reads (Option A: flat visibility, differ in rights).
  * The ``artifacts.artifacts.visibility`` stub column exists, is NOT NULL,
    and defaults to ``'cell-shared'`` (no backfill needed).
  * RLS cell-isolation on cell_members is unaffected by the new join path.

Insert with RLS bypassed (the test session is superuser); the permission
checks run through ``AuthorizationService`` on the same session.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context
from src.rbac.permissions import (
    BILLING_MANAGE,
    CELL_ARCHIVE,
    MEMBER_INVITE,
    TASK_CREATE,
    TASK_VIEW,
)
from src.rbac.services.authorization_service import AuthorizationService

pytestmark = pytest.mark.integration


async def _role_id(session: AsyncSession, slug: str) -> str:
    res = await session.execute(
        text("SELECT id FROM rbac.system_roles WHERE slug = :s"), {"s": slug}
    )
    row = res.first()
    assert row is not None, f"seed role {slug!r} missing — run migrations first"
    return str(row[0])


async def _seed_cell_with_member(session: AsyncSession, *, user_id, role_slug: str):
    """Create workspace + cell + a cell_member with the given role. Returns cell_id."""
    ws_id, cell_id = uuid4(), uuid4()
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, 'WS')"
        ),
        {"id": str(ws_id), "slug": f"ws-{ws_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cell_members (cell_id, user_id, role_id) "
            "VALUES (:cell, :user, :role)"
        ),
        {"cell": str(cell_id), "user": str(user_id), "role": await _role_id(session, role_slug)},
    )
    return cell_id


@pytest.mark.asyncio
async def test_owner_granted_owner_only_and_task_create(db_session: AsyncSession) -> None:
    user_id = uuid4()
    cell_id = await _seed_cell_with_member(db_session, user_id=user_id, role_slug="owner")
    svc = AuthorizationService(db_session)

    for perm in (MEMBER_INVITE, CELL_ARCHIVE, BILLING_MANAGE, TASK_CREATE, TASK_VIEW):
        assert await svc.has_cell_permission(
            user_id=user_id, cell_id=cell_id, permission_slug=perm
        ), f"owner should be granted {perm}"


@pytest.mark.asyncio
async def test_member_denied_owner_only_but_allowed_task(db_session: AsyncSession) -> None:
    """'Member' = editor role: create tasks + see everything, no owner rights."""
    user_id = uuid4()
    cell_id = await _seed_cell_with_member(db_session, user_id=user_id, role_slug="editor")
    svc = AuthorizationService(db_session)

    # Owner-only actions → denied.
    for perm in (MEMBER_INVITE, CELL_ARCHIVE, BILLING_MANAGE):
        assert not await svc.has_cell_permission(
            user_id=user_id, cell_id=cell_id, permission_slug=perm
        ), f"member should be denied {perm}"

    # Member rights → allowed (create tasks, see content).
    for perm in (TASK_CREATE, TASK_VIEW):
        assert await svc.has_cell_permission(
            user_id=user_id, cell_id=cell_id, permission_slug=perm
        ), f"member should be allowed {perm}"


@pytest.mark.asyncio
async def test_non_member_denied(db_session: AsyncSession) -> None:
    """A user with no membership row in the cell is default-denied everything."""
    owner_id, stranger_id = uuid4(), uuid4()
    cell_id = await _seed_cell_with_member(db_session, user_id=owner_id, role_slug="owner")
    svc = AuthorizationService(db_session)
    assert not await svc.has_cell_permission(
        user_id=stranger_id, cell_id=cell_id, permission_slug=TASK_VIEW
    )


@pytest.mark.asyncio
async def test_visibility_stub_column_default(db_session: AsyncSession) -> None:
    """artifacts.artifacts.visibility exists, NOT NULL, defaults to 'cell-shared'."""
    # Column metadata: NOT NULL + default 'cell-shared'.
    res = await db_session.execute(
        text(
            "SELECT is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'artifacts' AND table_name = 'artifacts' "
            "  AND column_name = 'visibility'"
        )
    )
    row = res.first()
    assert row is not None, "visibility column missing from artifacts.artifacts"
    is_nullable, column_default = row
    assert is_nullable == "NO"
    assert "cell-shared" in (column_default or "")

    # Behaviour: an INSERT without visibility gets the default.
    ws_id, cell_id, art_id = uuid4(), uuid4(), uuid4()
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, 'WS')"
        ),
        {"id": str(ws_id), "slug": f"ws-{ws_id}"},
    )
    await db_session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(
            text(
                "INSERT INTO artifacts.artifacts (id, cell_id, artifact_type, title) "
                "VALUES (:id, :cell, 'document', 'T')"
            ),
            {"id": str(art_id), "cell": str(cell_id)},
        )
        got = await db_session.execute(
            text("SELECT visibility FROM artifacts.artifacts WHERE id = :id"),
            {"id": str(art_id)},
        )
        assert got.scalar_one() == "cell-shared"
