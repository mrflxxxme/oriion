"""GET /api/v1/agent-archetypes — read-only system catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src.agents.schemas import AgentArchetypeOut
from src.agents.services.archetype_service import ArchetypeService

router = APIRouter(prefix="/agent-archetypes", tags=["agents"])


def get_archetype_service(db: AsyncSession = Depends(get_db)) -> ArchetypeService:
    return ArchetypeService(db)


@router.get("", response_model=list[AgentArchetypeOut])
async def list_archetypes(
    vertical_slug: str | None = Query(default=None),
    service: ArchetypeService = Depends(get_archetype_service),
) -> list[AgentArchetypeOut]:
    rows = await service.list_active(vertical_slug=vertical_slug)
    return [AgentArchetypeOut.model_validate(r) for r in rows]
