"""ArchetypeService — read-only catalog over agents.agent_archetypes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.exceptions import AgentArchetypeNotFound
from src.agents.models import AgentArchetype


class ArchetypeService:
    """Wave 0 system-level catalog. Writes land in Wave 1+ when role
    authoring + vertical-template editor ship."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, *, vertical_slug: str | None = None) -> list[AgentArchetype]:
        stmt = select(AgentArchetype).where(
            AgentArchetype.is_active.is_(True),
            AgentArchetype.deprecated_at.is_(None),
        )
        if vertical_slug is not None:
            stmt = stmt.where(AgentArchetype.vertical_slug == vertical_slug)
        stmt = stmt.order_by(
            AgentArchetype.vertical_slug, AgentArchetype.role_category, AgentArchetype.slug
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows)

    async def get_by_id(self, archetype_id: UUID) -> AgentArchetype:
        row = await self._session.get(AgentArchetype, archetype_id)
        if row is None:
            raise AgentArchetypeNotFound(f"archetype {archetype_id} not found")
        return row
