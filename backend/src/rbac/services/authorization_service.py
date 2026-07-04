"""AuthorizationService — central allow-checks (two role stores).

There are two role-binding stores in the system:

* ``rbac.role_assignments`` — the general (user, scope_type, scope_id, role)
  binding with optional ``expires_at``. Read by ``has_permission``. Reserved
  for future workspace-scoped / delegated / time-boxed grants; NOT populated
  by any Wave-1 code path.
* ``multitenancy.cell_members.role_id`` — the **populated** cell-membership
  role store (Owner set at register via the SECURITY DEFINER bootstrap;
  editable via the cells router). Read by ``has_cell_permission``.

Phase 01.7 (Owner/Member RBAC enforcement, ADR-014 §1, Option A flat
visibility) enforces off ``cell_members`` because that is the store that is
actually written — see DECISIONS-LOG 01.7 impl fork. ``has_permission`` is
left intact for the role_assignments path a later wave will use.

Wave 0/1: no caching. A later wave MAY introduce a per-(user,scope) cache
invalidated by role_assigned.v1 / role_revoked.v1 / member.role_changed.v1
events. Both methods take an explicit ``session`` so caching can be added
without breaking call sites.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.rbac.models import Permission, RoleAssignment, RolePermission

ScopeType = Literal["workspace", "cell"]


class AuthorizationService:
    """Wave-0 authorization checker (no cache).

    Instances are cheap (just holds a reference to AsyncSession); construct
    one per request via FastAPI Depends() or pass into services that need
    to gate calls.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_permission(
        self,
        *,
        user_id: UUID,
        scope_type: ScopeType,
        scope_id: UUID,
        permission_slug: str,
    ) -> bool:
        """Return True iff the user is granted permission in the scope.

        Filters:
          * role_assignments.user_id == user_id
          * role_assignments.scope_type == scope_type
          * role_assignments.scope_id == scope_id
          * permissions.slug == permission_slug
          * role_assignments.expires_at IS NULL OR > now()
        """
        now = datetime.now(UTC)
        stmt = (
            select(RoleAssignment.id)
            .join(
                RolePermission,
                RolePermission.role_id == RoleAssignment.role_id,
            )
            .join(
                Permission,
                Permission.id == RolePermission.permission_id,
            )
            .where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.scope_type == scope_type,
                RoleAssignment.scope_id == scope_id,
                Permission.slug == permission_slug,
                # expires_at IS NULL OR > now()
                (RoleAssignment.expires_at.is_(None)) | (RoleAssignment.expires_at > now),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def has_cell_permission(
        self,
        *,
        user_id: UUID,
        cell_id: UUID,
        permission_slug: str,
    ) -> bool:
        """Return True iff the user's cell-membership role grants the permission.

        Resolves the caller's role from ``multitenancy.cell_members`` (the
        populated store — Owner at register, editable via the cells router)
        and joins it through ``rbac.role_permissions → rbac.permissions``.
        This is the enforcement authority for Phase 01.7 (Owner/Member, Option
        A flat visibility): membership = cell access (all reads), and the role
        grants decide the write/manage rights.

        A cross-context raw SELECT is used deliberately: the ``rbac`` context
        does not import ``multitenancy`` ORM models (cross-context FKs are not
        enforced at the ORM layer per ADR-024). The query is fully
        parameterised — no interpolation of caller input.

        Returns False when the user is not a member of the cell OR the member's
        role does not grant ``permission_slug`` (default-deny).
        """
        stmt = text(
            """
            SELECT 1
            FROM multitenancy.cell_members cm
            JOIN rbac.role_permissions rp ON rp.role_id = cm.role_id
            JOIN rbac.permissions p ON p.id = rp.permission_id
            WHERE cm.cell_id = :cell_id
              AND cm.user_id = :user_id
              AND p.slug = :slug
            LIMIT 1
            """
        )
        result = await self._session.execute(
            stmt,
            {"cell_id": str(cell_id), "user_id": str(user_id), "slug": permission_slug},
        )
        return result.first() is not None
