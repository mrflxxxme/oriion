"""Request-scoped tenant context dependency — wraps get_db + set_tenant_context.

Per Phase 00.5 Topic 1 (RLS Option A, 2026-05-20) this is the single
production caller of `_shared.db.rls.set_tenant_context`. Routes that need
tenant-scoped DB access depend on `get_tenant_db_session` instead of the
raw `get_db` so every query inside the handler is RLS-scoped via the
3-GUC `(app.current_user_id, app.current_workspace_id, app.current_cell_id)`.

Wave-0 single-membership simplification:
  * Each user belongs to exactly one workspace (provisioned at register).
  * Each workspace has exactly one default cell.
  * Resolution: WorkspaceRepository.find_by_user_id returns the singleton
    workspace; CellRepository.find_first_for_workspace returns the default
    cell. Wave-1+ swaps this for an `active_workspace_id` JWT claim.

Bootstrap exception:
  * `POST /api/v1/auth/register` runs through `get_db` (no tenant context yet
    by definition — the user is being created in the request). The actual
    multitenancy provisioning calls `multitenancy.bootstrap_first_workspace`
    (SECURITY DEFINER) per ADR-014 amendment 2026-05-20.

Error semantics:
  * Authenticated user with no workspace membership → `TenantContextMissing`
    raised (502/500 surface). This indicates a Wave-0 invariant violation
    (every user must have a workspace at register-time) and should never
    happen in production; surfacing it instead of silent default-deny is
    a defence-in-depth choice.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.rls import set_tenant_context
from src._shared.db.session import get_db
from src.iam.middleware import AuthenticatedUser, get_current_user


class TenantContextMissingError(RuntimeError):
    """Raised when an authenticated user has no workspace membership.

    Wave-0 invariant violation. Bubbles to a 500 unless the caller maps it.
    """


async def _resolve_tenant_ids(
    *,
    session: AsyncSession,
    user_id: UUID,
) -> tuple[UUID, UUID]:
    """Wave-0 single-membership lookup → (workspace_id, cell_id).

    Calls the SECURITY DEFINER SQL function
    ``multitenancy.resolve_user_first_membership(p_user_id)`` (introduced by
    migration ``multitenancy/0005_bootstrap_first_workspace_function.py``) so
    the membership lookup bypasses RLS. The caller has no tenant GUC set
    yet — by design, that's what we're about to resolve — so a direct
    ``SELECT FROM multitenancy.cell_members`` would hit default-deny.

    Wave-0 simplification: there is only one workspace per user and one
    default cell per workspace, so the function returns at most one row.
    """
    result = await session.execute(
        text("SELECT workspace_id, cell_id FROM multitenancy.resolve_user_first_membership(:uid)"),
        {"uid": str(user_id)},
    )
    row = result.first()
    if row is None:
        raise TenantContextMissingError(
            f"User {user_id} has no cell membership — Wave-0 invariant violation "
            "(every user must have a workspace + default cell from register)."
        )
    workspace_id, cell_id = row
    return UUID(str(workspace_id)), UUID(str(cell_id))


async def get_tenant_db_session(
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields an AsyncSession with 3-GUC RLS context set.

    Usage::

        @router.get("/api/v1/cells/{cell_id}/...")
        async def handler(
            db: AsyncSession = Depends(get_tenant_db_session),
        ) -> ...:
            # All queries here are RLS-scoped to the auth'd user's
            # (workspace_id, cell_id) via Postgres session-local GUCs.
            ...

    The dependency chains through `get_current_user` (JWT verification) and
    `get_db` (raw session) so failures at either layer produce the standard
    401 / 500 envelopes upstream.
    """
    workspace_id, cell_id = await _resolve_tenant_ids(
        session=db,
        user_id=auth.user.id,
    )
    async with set_tenant_context(
        db,
        workspace_id=workspace_id,
        cell_id=cell_id,
        user_id=auth.user.id,
    ) as scoped:
        yield scoped


async def get_current_cell_id(
    db: AsyncSession = Depends(get_tenant_db_session),
) -> UUID:
    """Resolved current-cell UUID from the RLS GUC set by get_tenant_db_session.

    For routers that operate on "my current cell" without a ``cell_id`` path
    param (Wave-0 single-cell). FastAPI caches the ``get_tenant_db_session``
    dependency per request, so this reads the same scoped session.
    """
    value = (await db.execute(text("SELECT _shared.current_cell_id()"))).scalar_one()
    if value is None:
        raise TenantContextMissingError(
            "no current cell in tenant context — Wave-0 invariant violation"
        )
    return UUID(str(value))
