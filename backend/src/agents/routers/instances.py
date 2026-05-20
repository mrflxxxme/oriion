"""GET /api/v1/cells/{cell_id}/agents — list cell-scoped agent instances."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import get_tenant_db_session
from src.agents.models import AgentInstance
from src.agents.schemas import AgentInstanceOut

router = APIRouter(prefix="/cells/{cell_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentInstanceOut])
async def list_cell_agents(
    cell_id: UUID,
    db: AsyncSession = Depends(get_tenant_db_session),
) -> list[AgentInstanceOut]:
    """List active agent instances for the cell.

    F-SEC-H1 fix (Phase 00.5b audit): uses `get_tenant_db_session` so the
    3-GUC RLS context is set before the SELECT runs. FORCE-RLS policy on
    `agents.agent_instances` filters by `app.current_cell_id` — without
    the GUC the SELECT would return zero rows under `oriion_app` role.
    """
    stmt = select(AgentInstance).where(
        AgentInstance.cell_id == cell_id,
        AgentInstance.archived_at.is_(None),
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [AgentInstanceOut.model_validate(r) for r in rows]
