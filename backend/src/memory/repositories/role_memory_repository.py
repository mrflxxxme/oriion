"""Role memory repository — memory.role_memory_entries.

Scoped by cell (RLS) AND ``agent_id`` (explicit filter) so one agent-instance
never reads another's personal memory even within the same cell.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.models import RoleMemoryEntry


class RoleMemoryRepository:
    """Per agent-instance personal-memory access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        agent_id: UUID,
        content: str,
        kind: str = "preference",
        title: str | None = None,
        embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
        tags: Sequence[str] | None = None,
        source: str = "manual",
        contains_pii: bool = False,
        created_by_user_id: UUID | None = None,
    ) -> RoleMemoryEntry:
        row = RoleMemoryEntry(
            cell_id=cell_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            kind=kind,
            title=title,
            content=content,
            embedding=list(embedding) if embedding is not None else None,
            embedding_model=embedding_model,
            tags=list(tags or []),
            source=source,
            contains_pii=contains_pii,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_id(self, entry_id: UUID) -> RoleMemoryEntry | None:
        return await self._session.get(RoleMemoryEntry, entry_id)

    async def delete_by_id(self, entry_id: UUID, *, agent_id: UUID) -> bool:
        result = await self._session.execute(
            delete(RoleMemoryEntry)
            .where(RoleMemoryEntry.id == entry_id, RoleMemoryEntry.agent_id == agent_id)
            .returning(RoleMemoryEntry.id)
        )
        return result.scalar_one_or_none() is not None

    async def count_by_agent(self, cell_id: UUID, agent_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(RoleMemoryEntry)
            .where(RoleMemoryEntry.cell_id == cell_id, RoleMemoryEntry.agent_id == agent_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_recent(
        self, cell_id: UUID, agent_id: UUID, *, limit: int, offset: int = 0
    ) -> Sequence[RoleMemoryEntry]:
        stmt = (
            select(RoleMemoryEntry)
            .where(RoleMemoryEntry.cell_id == cell_id, RoleMemoryEntry.agent_id == agent_id)
            .order_by(RoleMemoryEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def search_by_embedding(
        self,
        cell_id: UUID,
        agent_id: UUID,
        query_embedding: Sequence[float],
        *,
        limit: int,
    ) -> list[tuple[RoleMemoryEntry, float]]:
        """Top-``limit`` nearest role-memory entries for one agent (cosine ``<=>``)."""
        distance = RoleMemoryEntry.embedding.cosine_distance(list(query_embedding))
        stmt = (
            select(RoleMemoryEntry, distance.label("distance"))
            .where(
                RoleMemoryEntry.cell_id == cell_id,
                RoleMemoryEntry.agent_id == agent_id,
                RoleMemoryEntry.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], float(row[1])) for row in rows]
