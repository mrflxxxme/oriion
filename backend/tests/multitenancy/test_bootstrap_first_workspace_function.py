"""Bootstrap-function focused test — exercises the SECURITY DEFINER path.

Per Phase 00.5 Topic 1 (RLS Option A, 2026-05-20) the register-time
bootstrap escapes the FORCE-RLS INSERT WITH CHECK policies on
multitenancy.{workspaces, cells, cell_members} via the SECURITY DEFINER
function ``multitenancy.bootstrap_first_workspace(...)``. This file
asserts the function's contract directly, independently of register-flow:

  * Fresh-create returns (workspace_id, cell_id, schema_name,
    was_replay=false) and persists all 4 rows (workspace, cell,
    cell_member, per-cell schema).
  * Re-invocation with same slug returns (existing_workspace_id,
    existing_cell_id, ..., was_replay=true) — idempotent replay.
  * Function executes successfully under `SET LOCAL ROLE oriion_app`
    (the production failure mode that direct ORM INSERTs would hit).
  * cell_member is created with `rbac.system_roles.cell.owner` role.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration]


async def _insert_test_user(session: AsyncSession, *, email: str) -> str:
    """Insert a synthetic user (oriion superuser, no RLS) and return uuid str.

    iam.users has no RLS policy (ADR-009 §scope — iam is non-tenant), so
    a direct INSERT under any role works as long as the role has
    INSERT on iam.users. The testcontainers owner role has it.
    """
    result = await session.execute(
        text(
            "INSERT INTO iam.users (email, password_hash, email_verified_at) "
            "VALUES (:email, 'argon2id$dummy', now()) "
            "RETURNING id::text"
        ),
        {"email": email},
    )
    return str(result.scalar())


async def test_inserts_workspace_cell_cell_member_under_oriion_app_role(
    db_engine: AsyncEngine,
) -> None:
    """Under `SET LOCAL ROLE oriion_app`, bootstrap_first_workspace must
    successfully provision the 4-row tuple even though direct INSERTs
    against the same tables would fail (FORCE RLS without GUC).

    Canary test for Architecture H1 + H2 (Phase 00.5 AC#1).
    """
    # Setup: insert the user as owner (no RLS on iam.users), then switch
    # to oriion_app for the bootstrap call.
    email = f"bootstrap-canary-{uuid4().hex[:8]}@example.com"
    async with db_engine.connect() as conn, conn.begin():
        user_id = await _insert_test_user(
            AsyncSession(bind=conn, expire_on_commit=False),
            email=email,
        )

    # Bootstrap call under oriion_app role
    slug = f"bootstrap-canary-{uuid4().hex[:8]}"
    display_name = "Bootstrap Canary"
    async with db_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        await session.execute(text("SET LOCAL ROLE oriion_app"))

        # Sanity: under oriion_app + no GUC, a direct INSERT should fail
        # (FORCE-RLS INSERT WITH CHECK policy requires
        # _shared.current_user_id() IS NOT NULL).
        # We don't assert the failure here (it would dirty the TX);
        # the existence of bootstrap_first_workspace is itself the answer.

        result = await session.execute(
            text(
                "SELECT workspace_id::text, cell_id::text, schema_name, was_replay "
                "FROM multitenancy.bootstrap_first_workspace(:uid, :slug, :display)"
            ),
            {"uid": user_id, "slug": slug, "display": display_name},
        )
        row = result.first()
        assert row is not None
        workspace_id, cell_id, schema_name, was_replay = row
        assert workspace_id
        assert cell_id
        assert schema_name == f"cell_{cell_id.replace('-', '_')}"
        assert was_replay is False

    # Verify side-effects from a fresh owner-role session (no RLS).
    async with db_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # 1. Workspace persisted
        ws_count = await session.execute(
            text("SELECT count(*) FROM multitenancy.workspaces WHERE id = :w"),
            {"w": workspace_id},
        )
        assert ws_count.scalar() == 1

        # 2. Cell persisted with default slug
        cell_row = await session.execute(
            text("SELECT slug, display_name FROM multitenancy.cells WHERE id = :c"),
            {"c": cell_id},
        )
        cr = cell_row.first()
        assert cr is not None
        assert cr[0] == "default"
        assert cr[1] == "Default cell"

        # 3. cell_member persisted with 'owner' role (rbac.system_roles seed)
        member_row = await session.execute(
            text(
                "SELECT m.user_id::text, sr.slug "
                "FROM multitenancy.cell_members m "
                "JOIN rbac.system_roles sr ON sr.id = m.role_id "
                "WHERE m.cell_id = :c"
            ),
            {"c": cell_id},
        )
        mr = member_row.first()
        assert mr is not None
        assert mr[0] == user_id
        assert mr[1] == "owner"

        # 4. Per-cell schema materialized
        schema_row = await session.execute(
            text("SELECT schema_name FROM information_schema.schemata " "WHERE schema_name = :s"),
            {"s": schema_name},
        )
        assert schema_row.scalar() == schema_name


async def test_replay_returns_existing_ids_with_was_replay_true(
    db_engine: AsyncEngine,
) -> None:
    """Second invocation with same slug → was_replay=true, same IDs."""
    email = f"bootstrap-replay-{uuid4().hex[:8]}@example.com"
    async with db_engine.connect() as conn, conn.begin():
        user_id = await _insert_test_user(
            AsyncSession(bind=conn, expire_on_commit=False),
            email=email,
        )

    slug = f"bootstrap-replay-{uuid4().hex[:8]}"
    display = "Replay test"

    async with db_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        r1 = (
            await session.execute(
                text(
                    "SELECT workspace_id::text, cell_id::text, was_replay "
                    "FROM multitenancy.bootstrap_first_workspace(:uid, :slug, :display)"
                ),
                {"uid": user_id, "slug": slug, "display": display},
            )
        ).first()
        assert r1 is not None
        ws1, cell1, replay1 = r1
        assert replay1 is False

    async with db_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        r2 = (
            await session.execute(
                text(
                    "SELECT workspace_id::text, cell_id::text, was_replay "
                    "FROM multitenancy.bootstrap_first_workspace(:uid, :slug, :display)"
                ),
                {"uid": user_id, "slug": slug, "display": display},
            )
        ).first()
        assert r2 is not None
        ws2, cell2, replay2 = r2
        assert replay2 is True
        assert ws2 == ws1
        assert cell2 == cell1


async def test_resolve_user_first_membership_returns_correct_tuple(
    db_engine: AsyncEngine,
) -> None:
    """Companion helper test: resolve_user_first_membership must return
    (workspace_id, cell_id) for the bootstrapped user even under default-deny
    RLS (the function is SECURITY DEFINER).
    """
    email = f"resolver-canary-{uuid4().hex[:8]}@example.com"
    async with db_engine.connect() as conn, conn.begin():
        user_id = await _insert_test_user(
            AsyncSession(bind=conn, expire_on_commit=False),
            email=email,
        )

    slug = f"resolver-canary-{uuid4().hex[:8]}"
    async with db_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        bootstrap = (
            await session.execute(
                text(
                    "SELECT workspace_id::text, cell_id::text "
                    "FROM multitenancy.bootstrap_first_workspace(:uid, :slug, :display)"
                ),
                {"uid": user_id, "slug": slug, "display": "Resolver"},
            )
        ).first()
        assert bootstrap is not None
        expected_ws, expected_cell = bootstrap

    # Resolver lookup under oriion_app + no GUC must succeed because the
    # helper is SECURITY DEFINER (bypasses cell_members_select_self_row).
    async with db_engine.connect() as conn, conn.begin():
        session = AsyncSession(bind=conn, expire_on_commit=False)
        await session.execute(text("SET LOCAL ROLE oriion_app"))

        row = (
            await session.execute(
                text(
                    "SELECT workspace_id::text, cell_id::text "
                    "FROM multitenancy.resolve_user_first_membership(:uid)"
                ),
                {"uid": user_id},
            )
        ).first()
        assert row is not None
        assert row[0] == expected_ws
        assert row[1] == expected_cell
