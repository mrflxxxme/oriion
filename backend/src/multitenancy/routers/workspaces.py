"""POST/GET /api/v1/workspaces — workspace CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.multitenancy.exceptions import WorkspaceNotFound, WorkspaceSlugConflict
from src.multitenancy.schemas import (
    WorkspaceCreate,
    WorkspaceOut,
    WorkspacePage,
)
from src.multitenancy.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(
    db: AsyncSession = Depends(get_db),
) -> WorkspaceService:
    return WorkspaceService(db)


@router.post(
    "",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreate,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceOut:
    try:
        workspace = await service.create_workspace(
            display_name=payload.display_name,
            slug=payload.slug,
            billing_email=payload.billing_email,
            plan_tier=payload.plan_tier,
            created_by_user_id=auth.user.id,
        )
    except IntegrityError as exc:
        # Unique-violation on the partial unique index over slug → 409.
        raise WorkspaceSlugConflict() from exc
    return WorkspaceOut.model_validate(workspace)


@router.get(
    "",
    response_model=WorkspacePage,
)
async def list_workspaces(
    auth: AuthenticatedUser = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspacePage:
    workspaces = await service.list_for_user(auth.user.id)
    return WorkspacePage(
        items=[WorkspaceOut.model_validate(w) for w in workspaces],
        next_cursor=None,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceOut,
)
async def get_workspace(
    workspace_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001 — auth required
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceOut:
    from uuid import UUID

    workspace = await service.find_by_id(UUID(workspace_id))
    if workspace is None:
        raise WorkspaceNotFound()
    return WorkspaceOut.model_validate(workspace)
