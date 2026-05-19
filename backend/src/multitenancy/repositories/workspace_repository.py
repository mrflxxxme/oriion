"""WorkspaceRepository — AsyncSession wrapper for multitenancy.workspaces."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.multitenancy.models import Cell, CellMember, Workspace

PlanTier = Literal["free", "starter", "pro", "enterprise"]


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, workspace_id: UUID) -> Workspace | None:
        return await self._session.get(Workspace, workspace_id)

    async def find_by_slug_active(self, slug: str) -> Workspace | None:
        """Lookup by slug excluding soft-deleted workspaces."""
        stmt = select(Workspace).where(
            Workspace.slug == slug,
            Workspace.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find_by_user_id(self, user_id: UUID) -> list[Workspace]:
        """Workspaces the user has any cell membership in.

        Uses JOIN over multitenancy.cells + multitenancy.cell_members; relies on
        RLS being either bypassed (service-account) or matching the calling
        user (which makes the JOIN trivially correct anyway).
        """
        stmt = (
            select(Workspace)
            .join(Cell, Cell.workspace_id == Workspace.id)
            .join(CellMember, CellMember.cell_id == Cell.id)
            .where(
                CellMember.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
            .distinct()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        slug: str,
        display_name: str,
        billing_email: str | None = None,
        plan_tier: PlanTier = "free",
    ) -> Workspace:
        workspace = Workspace(
            slug=slug,
            display_name=display_name,
            billing_email=billing_email,
            plan_tier=plan_tier,
        )
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def soft_delete(self, workspace_id: UUID) -> None:
        await self._session.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(deleted_at=datetime.now(UTC))
        )
