"""GET /api/v1/cells/{cell_id}/agents — list cell-scoped agent instances."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src.agents.models import AgentInstance
from src.agents.schemas import AgentInstanceOut

router = APIRouter(prefix="/cells/{cell_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentInstanceOut])
async def list_cell_agents(
    cell_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AgentInstanceOut]:
    """List active agent instances for the cell.

    RLS-protected via app.current_cell_id GUC — caller must run under
    `get_tenant_db_session` (Phase 00.5a middleware) for production. Wave 0
    handler reads from get_db directly; tenant context wiring lands when
    cell-scoped routers are migrated to get_tenant_db_session.
    """
    stmt = select(AgentInstance).where(
        AgentInstance.cell_id == cell_id,
        AgentInstance.archived_at.is_(None),
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [AgentInstanceOut.model_validate(r) for r in rows]
