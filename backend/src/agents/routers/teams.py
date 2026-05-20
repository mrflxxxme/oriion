"""POST /api/v1/cells/{cell_id}/teams — provision a team-preset into a cell."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import get_tenant_db_session
from src.agents.models import TeamPreset
from src.agents.schemas import (
    AgentInstanceOut,
    TeamProvisionRequest,
    TeamProvisionResponse,
)
from src.agents.services.team_provisioning_service import TeamProvisioningService
from src.iam.middleware import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/cells/{cell_id}/teams", tags=["agents"])


def get_team_provisioning_service(
    db: AsyncSession = Depends(get_tenant_db_session),
) -> TeamProvisioningService:
    return TeamProvisioningService(db)


@router.post(
    "",
    response_model=TeamProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_team(
    cell_id: UUID,
    payload: TeamProvisionRequest,
    db: AsyncSession = Depends(get_tenant_db_session),
    auth: AuthenticatedUser = Depends(get_current_user),
    service: TeamProvisioningService = Depends(get_team_provisioning_service),
) -> TeamProvisionResponse:
    instances = await service.provision_team(
        preset_slug=payload.preset_key,
        cell_id=cell_id,
        user_id=auth.user.id,
    )
    preset_stmt = select(TeamPreset).where(TeamPreset.slug == payload.preset_key)
    preset = (await db.execute(preset_stmt)).scalar_one()
    return TeamProvisionResponse(
        team_preset_id=preset.id,
        cell_id=cell_id,
        agent_instances=[AgentInstanceOut.model_validate(i) for i in instances],
    )
