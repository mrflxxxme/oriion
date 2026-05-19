"""AuditRepository — thin AsyncSession wrapper for audit.audit_log.

Append-only by trigger contract (audit.deny_update_delete on the parent
table). This class deliberately exposes no update/delete methods.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.models import AuditLog


class AuditRepository:
    """Thin repo over audit.audit_log. INSERT + read-only SELECTs only."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        actor_type: str,
        actor_id: UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        cell_id: UUID | None = None,
        workspace_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Insert one row. Relies on the caller's outer transaction for COMMIT.

        ``id`` and ``ts`` are left DB-defaulted (gen_random_uuid() / now())
        so that monotonicity of ts is server-controlled (callers cannot
        forge an earlier timestamp to evade retention partitions).
        """
        row = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            cell_id=cell_id,
            workspace_id=workspace_id,
            payload=payload,
            ip=ip,
            user_agent=user_agent,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_by_actor(
        self,
        actor_id: UUID,
        *,
        limit: int = 50,
        cursor: datetime | None = None,
    ) -> Sequence[AuditLog]:
        """Reverse-chronological page of events for one actor.

        ``cursor`` is the ``ts`` value of the previous page's last row;
        rows with strictly smaller ``ts`` are returned. Combined with the
        ``(actor_id, ts DESC)`` partial index this is keyset pagination.
        """
        stmt = select(AuditLog).where(AuditLog.actor_id == actor_id)
        if cursor is not None:
            stmt = stmt.where(AuditLog.ts < cursor)
        stmt = stmt.order_by(AuditLog.ts.desc()).limit(limit)
        return (await self._session.execute(stmt)).scalars().all()

    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: UUID,
        *,
        limit: int = 50,
        cursor: datetime | None = None,
    ) -> Sequence[AuditLog]:
        """Reverse-chronological page of events touching one resource."""
        stmt = select(AuditLog).where(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        )
        if cursor is not None:
            stmt = stmt.where(AuditLog.ts < cursor)
        stmt = stmt.order_by(AuditLog.ts.desc()).limit(limit)
        return (await self._session.execute(stmt)).scalars().all()
