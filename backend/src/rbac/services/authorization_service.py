"""AuthorizationService.has_permission — central allow-check.

Given (user, scope_type, scope_id, permission_slug), returns True iff the
user has at least one non-expired role assignment in that scope whose role
grants the requested permission. The implementation is a single JOIN over
role_assignments → role_permissions → permissions filtered by the inputs.

Wave 0: no caching. Wave 1+ MAY introduce per-(user,scope) cache invalidated
by role_assigned.v1 / role_revoked.v1 / role_expired.v1 events (see
contract README "Computing effective permissions"). The function shape
intentionally accepts an explicit `session` so caching can be added without
breaking the call site.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
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
