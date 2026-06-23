"""Role memory service — per agent-instance personal memory.

Scoped by cell (RLS) AND ``agent_id`` so an agent never reads another agent's
personal memory even within the same cell. Logs ids/counts only.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import structlog

from src.memory.exceptions import MemoryEntryNotFound
from src.memory.models import ROLE_MEMORY_SOFT_CAP, RoleMemoryEntry
from src.memory.repositories.role_memory_repository import RoleMemoryRepository
from src.memory.services.embedder import Embedder
from src.memory.services.memory_service import cosine_similarity_from_distance

logger = structlog.get_logger(__name__)


class RoleMemoryService:
    """Per agent-instance personal memory: store + recall."""

    def __init__(self, repo: RoleMemoryRepository, embedder: Embedder) -> None:
        self._repo = repo
        self._embedder = embedder

    async def add(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        agent_id: UUID,
        content: str,
        kind: str = "preference",
        title: str | None = None,
        tags: Sequence[str] | None = None,
        source: str = "manual",
        contains_pii: bool = False,
        created_by_user_id: UUID | None = None,
    ) -> tuple[RoleMemoryEntry, bool]:
        """Embed + store one role-memory entry. Returns ``(entry, soft_cap_exceeded)``."""
        (vector,) = await self._embedder.embed_documents([content])
        entry = await self._repo.insert(
            cell_id=cell_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
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
        count = await self._repo.count_by_agent(cell_id, agent_id)
        over_cap = count > ROLE_MEMORY_SOFT_CAP
        if over_cap:
            logger.warning(
                "memory.role.soft_cap_exceeded",
                cell_id=str(cell_id),
                agent_id=str(agent_id),
                count=count,
                cap=ROLE_MEMORY_SOFT_CAP,
            )
        if contains_pii:
            logger.info(
                "memory.role.pii_stored",
                cell_id=str(cell_id),
                agent_id=str(agent_id),
                entry_id=str(entry.id),
                kind=kind,
            )
        return entry, over_cap

    async def search(
        self, *, cell_id: UUID, agent_id: UUID, query: str, limit: int = 10
    ) -> list[tuple[RoleMemoryEntry, float]]:
        query_vector = await self._embedder.embed_query(query)
        hits = await self._repo.search_by_embedding(cell_id, agent_id, query_vector, limit=limit)
        return [(entry, cosine_similarity_from_distance(distance)) for entry, distance in hits]

    async def list_recent(
        self, *, cell_id: UUID, agent_id: UUID, limit: int = 50, offset: int = 0
    ) -> Sequence[RoleMemoryEntry]:
        return await self._repo.list_recent(cell_id, agent_id, limit=limit, offset=offset)

    async def delete(self, *, cell_id: UUID, agent_id: UUID, entry_id: UUID) -> None:
        deleted = await self._repo.delete_by_id(entry_id, agent_id=agent_id)
        if not deleted:
            raise MemoryEntryNotFound(str(entry_id))
        logger.info(
            "memory.role.deleted",
            cell_id=str(cell_id),
            agent_id=str(agent_id),
            entry_id=str(entry_id),
        )
