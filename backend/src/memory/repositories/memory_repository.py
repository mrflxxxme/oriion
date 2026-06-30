"""Cell memory repository — memory.memory_entries (cell-isolated via RLS).

RLS scopes every statement to the active tenant cell; the explicit ``cell_id``
filters are kept as defense-in-depth (a missing GUC ⇒ default-deny already).
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.models import MemoryEntry


class CellMemoryRepository:
    """Per-cell shared-memory access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        content: str,
        kind: str = "fact",
        title: str | None = None,
        embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
        tags: Sequence[str] | None = None,
        source: str = "manual",
        contains_pii: bool = False,
        created_by_user_id: UUID | None = None,
    ) -> MemoryEntry:
        row = MemoryEntry(
            cell_id=cell_id,
            workspace_id=workspace_id,
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

    async def get_by_id(self, entry_id: UUID) -> MemoryEntry | None:
        return await self._session.get(MemoryEntry, entry_id)

    async def delete_by_id(self, entry_id: UUID, *, cell_id: UUID) -> bool:
        # Defense-in-depth: scope the delete to the active cell explicitly (RLS
        # FORCE already blocks cross-cell deletes; this matches the other methods).
        result = await self._session.execute(
            delete(MemoryEntry)
            .where(MemoryEntry.id == entry_id, MemoryEntry.cell_id == cell_id)
            .returning(MemoryEntry.id)
        )
        return result.scalar_one_or_none() is not None

    async def count_by_cell(self, cell_id: UUID) -> int:
        stmt = select(func.count()).select_from(MemoryEntry).where(MemoryEntry.cell_id == cell_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_recent(
        self, cell_id: UUID, *, limit: int, offset: int = 0
    ) -> Sequence[MemoryEntry]:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.cell_id == cell_id)
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def search_by_embedding(
        self, cell_id: UUID, query_embedding: Sequence[float], *, limit: int
    ) -> list[tuple[MemoryEntry, float]]:
        """Top-``limit`` nearest entries by cosine distance (HNSW ``<=>``).

        Returns ``(entry, cosine_distance)`` pairs; distance ∈ [0, 2], lower is
        closer. The service layer converts distance → similarity score.
        """
        distance = MemoryEntry.embedding.cosine_distance(list(query_embedding))
        stmt = (
            select(MemoryEntry, distance.label("distance"))
            .where(MemoryEntry.cell_id == cell_id, MemoryEntry.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], float(row[1])) for row in rows]
