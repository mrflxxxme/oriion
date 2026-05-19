"""CellRepository — AsyncSession wrapper for multitenancy.cells."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.multitenancy.models import Cell, Workspace


class CellRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, cell_id: UUID) -> Cell | None:
        return await self._session.get(Cell, cell_id)

    async def find_by_workspace_slug(self, workspace_id: UUID, slug: str) -> Cell | None:
        stmt = select(Cell).where(
            Cell.workspace_id == workspace_id,
            Cell.slug == slug,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        limit: int = 50,
        cursor: str | None = None,  # noqa: ARG002 — cursor reserved for Wave 1+
    ) -> list[Cell]:
        """List non-archived cells in the workspace.

        Cursor pagination is forward-declared in the API contract but
        Wave 0 returns up to `limit` rows ordered by created_at DESC; the
        next_cursor field will be wired up when traffic motivates it.
        """
        stmt = (
            select(Cell)
            .where(
                Cell.workspace_id == workspace_id,
                Cell.archived_at.is_(None),
            )
            .order_by(Cell.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_workspace_slug(self, workspace_slug: str, *, limit: int = 50) -> list[Cell]:
        """Helper for tests / debug: list cells by workspace slug."""
        stmt = (
            select(Cell)
            .join(Workspace, Workspace.id == Cell.workspace_id)
            .where(
                Workspace.slug == workspace_slug,
                Workspace.deleted_at.is_(None),
                Cell.archived_at.is_(None),
            )
            .order_by(Cell.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        workspace_id: UUID,
        slug: str,
        display_name: str,
        vertical_template_slug: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Cell:
        cell = Cell(
            workspace_id=workspace_id,
            slug=slug,
            display_name=display_name,
            vertical_template_slug=vertical_template_slug,
            settings_jsonb=settings if settings is not None else {},
        )
        self._session.add(cell)
        await self._session.flush()
        return cell

    async def archive(self, cell_id: UUID) -> None:
        await self._session.execute(
            update(Cell).where(Cell.id == cell_id).values(archived_at=datetime.now(UTC))
        )
