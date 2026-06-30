"""Cell memory service — embed, store (soft-cap), similarity search, delete.

SECURITY: logs only ids/counts/kind — never entry content or embeddings.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import structlog

from src.memory.exceptions import MemoryEntryNotFound
from src.memory.models import CELL_MEMORY_SOFT_CAP, MemoryEntry
from src.memory.repositories.memory_repository import CellMemoryRepository
from src.memory.services.embedder import Embedder

logger = structlog.get_logger(__name__)


def cosine_similarity_from_distance(cosine_distance: float) -> float:
    """pgvector cosine distance (``<=>``) = 1 - cosine similarity."""
    return 1.0 - cosine_distance


class CellMemoryService:
    """Cell-level shared memory: store + RAG-recall, cell-isolated via RLS."""

    def __init__(self, repo: CellMemoryRepository, embedder: Embedder) -> None:
        self._repo = repo
        self._embedder = embedder

    async def add(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        content: str,
        kind: str = "fact",
        title: str | None = None,
        tags: Sequence[str] | None = None,
        source: str = "manual",
        contains_pii: bool = False,
        created_by_user_id: UUID | None = None,
    ) -> tuple[MemoryEntry, bool]:
        """Embed + store one entry. Returns ``(entry, soft_cap_exceeded)``.

        Soft cap is advisory (grill Q7): the entry is still stored; the flag lets
        the API surface a cleanup hint. No eviction, no hard reject.
        """
        (vector,) = await self._embedder.embed_documents([content])
        entry = await self._repo.insert(
            cell_id=cell_id,
            workspace_id=workspace_id,
            content=content,
            kind=kind,
            title=title,
            embedding=vector,
            embedding_model=self._embedder.model_name,
            tags=tags,
            source=source,
            contains_pii=contains_pii,
            created_by_user_id=created_by_user_id,
        )
        count = await self._repo.count_by_cell(cell_id)
        over_cap = count > CELL_MEMORY_SOFT_CAP
        if over_cap:
            logger.warning(
                "memory.cell.soft_cap_exceeded",
                cell_id=str(cell_id),
                count=count,
                cap=CELL_MEMORY_SOFT_CAP,
            )
        if contains_pii:
            # ADR-011 privacy: PII-tagged memory is audit-logged (id only).
            logger.info(
                "memory.cell.pii_stored",
                cell_id=str(cell_id),
                entry_id=str(entry.id),
                kind=kind,
            )
        return entry, over_cap

    async def search(
        self, *, cell_id: UUID, query: str, limit: int = 10
    ) -> list[tuple[MemoryEntry, float]]:
        """Top-``limit`` entries by cosine similarity to ``query`` (desc)."""
        query_vector = await self._embedder.embed_query(query)
        hits = await self._repo.search_by_embedding(cell_id, query_vector, limit=limit)
        return [(entry, cosine_similarity_from_distance(distance)) for entry, distance in hits]

    async def list_recent(
        self, *, cell_id: UUID, limit: int = 50, offset: int = 0
    ) -> Sequence[MemoryEntry]:
        return await self._repo.list_recent(cell_id, limit=limit, offset=offset)

    async def delete(self, *, cell_id: UUID, entry_id: UUID) -> None:
        deleted = await self._repo.delete_by_id(entry_id, cell_id=cell_id)
        if not deleted:
            raise MemoryEntryNotFound(str(entry_id))
        logger.info("memory.cell.deleted", cell_id=str(cell_id), entry_id=str(entry_id))
