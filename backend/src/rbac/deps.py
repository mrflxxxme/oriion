"""FastAPI permission guards for Owner/Member RBAC enforcement (Phase 01.7).

``require_cell_permission(slug)`` returns a FastAPI dependency that:

  1. resolves the authenticated user (``get_current_user``),
  2. resolves the current cell + a 3-GUC RLS-scoped session
     (``get_tenant_db_session`` / ``get_current_cell_id``),
  3. checks ``AuthorizationService.has_cell_permission`` for the given
     permission slug against the user's ``cell_members`` role,
  4. raises ``PermissionDenied`` (403) on a miss.

Design (ADR-014 §1, Option A — flat visibility):
  * Membership = cell access → all **reads** need only ``get_current_user`` +
    tenant context (Member sees everything). Guards are applied ONLY to
    Owner-only actions (member management, role assignment, cell delete,
    billing management).
  * The check reads ``multitenancy.cell_members`` through the RLS-scoped
    session, so a user can only ever match their own cell's membership row —
    cross-cell escalation is impossible even before the permission join.

Usage::

    @router.post(
        "/{cell_id}/members/invite",
        dependencies=[Depends(require_cell_permission(MEMBER_INVITE))],
    )
    async def invite_member(...): ...

The guard is a ``dependencies=[...]`` side-effect (it yields nothing the
handler needs), so handlers keep their existing signatures.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import (
    get_current_cell_id,
    get_tenant_db_session,
)
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.rbac.exceptions import PermissionDenied
from src.rbac.services.authorization_service import AuthorizationService

_GuardDep = Callable[..., Coroutine[Any, Any, None]]


def require_cell_permission(permission_slug: str) -> _GuardDep:
    """Build a FastAPI dependency enforcing ``permission_slug`` in the cell.

    The returned coroutine raises :class:`PermissionDenied` (403) when the
    authenticated user's cell-membership role does not grant the permission.
    It returns ``None`` on success — attach via ``dependencies=[Depends(...)]``.
    """

    async def _guard(
        auth: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_tenant_db_session),
        cell_id: UUID = Depends(get_current_cell_id),
    ) -> None:
        granted = await AuthorizationService(db).has_cell_permission(
            user_id=auth.user.id,
            cell_id=cell_id,
            permission_slug=permission_slug,
        )
        if not granted:
            raise PermissionDenied(f"missing permission '{permission_slug}' in the current cell")

    return _guard
