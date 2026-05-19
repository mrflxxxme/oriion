"""Integration: rbac seed migration produced 6 roles + 15 permissions."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

EXPECTED_ROLES = {"owner", "admin", "editor", "viewer", "billing", "guest"}
EXPECTED_PERMS = {
    "workspace.view",
    "workspace.update",
    "workspace.delete",
    "cell.create",
    "cell.view",
    "cell.update",
    "cell.archive",
    "member.invite",
    "member.remove",
    "member.role_change",
    "billing.view",
    "billing.manage",
    "agent.run",
    "task.create",
    "task.view",
}


@pytest.mark.asyncio
async def test_six_built_in_roles_present(db_session: AsyncSession) -> None:
    res = await db_session.execute(text("SELECT slug, is_built_in FROM rbac.system_roles"))
    rows = {(r[0], bool(r[1])) for r in res.all()}
    for slug in EXPECTED_ROLES:
        assert (slug, True) in rows, f"missing or non-built-in role {slug!r}"


@pytest.mark.asyncio
async def test_fifteen_permissions_present(db_session: AsyncSession) -> None:
    res = await db_session.execute(text("SELECT slug FROM rbac.permissions"))
    slugs = {r[0] for r in res.all()}
    assert slugs >= EXPECTED_PERMS


@pytest.mark.asyncio
async def test_owner_role_has_all_15_permissions(db_session: AsyncSession) -> None:
    res = await db_session.execute(
        text(
            "SELECT p.slug FROM rbac.role_permissions rp "
            "JOIN rbac.system_roles r ON r.id = rp.role_id "
            "JOIN rbac.permissions p ON p.id = rp.permission_id "
            "WHERE r.slug = 'owner'"
        )
    )
    granted = {r[0] for r in res.all()}
    assert granted == EXPECTED_PERMS


@pytest.mark.asyncio
async def test_guest_role_has_only_task_view(db_session: AsyncSession) -> None:
    res = await db_session.execute(
        text(
            "SELECT p.slug FROM rbac.role_permissions rp "
            "JOIN rbac.system_roles r ON r.id = rp.role_id "
            "JOIN rbac.permissions p ON p.id = rp.permission_id "
            "WHERE r.slug = 'guest'"
        )
    )
    granted = {r[0] for r in res.all()}
    assert granted == {"task.view"}
