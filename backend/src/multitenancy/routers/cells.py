"""Cell + cell-member endpoints.

Two APIRouters live in this module:
  * `router` (default export) — `/api/v1/cells/*` endpoints (retrieve cell,
    list/invite/patch/remove members).
  * `workspace_cells_router` — `/api/v1/workspaces/{workspace_id}/cells`
    list + create endpoints. Kept separate because FastAPI's routing
    couldn't otherwise reach both prefixes cleanly under a single APIRouter.

The 00.2.5 integration phase mounts both routers in src/main.py with the
`/api/v1` prefix.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.multitenancy.exceptions import (
    CellNotFound,
    CellSlugConflict,
)
from src.multitenancy.models import Cell
from src.multitenancy.repositories.cell_repository import CellRepository
from src.multitenancy.schemas import (
    CellCreate,
    CellMemberOut,
    CellOut,
    CellPage,
    InvitationCreate,
    InvitationOut,
)
from src.multitenancy.services.cell_service import CellService

router = APIRouter(prefix="/cells", tags=["cells"])
workspace_cells_router = APIRouter(prefix="/workspaces/{workspace_id}/cells", tags=["cells"])


# ── inline payload schemas ────────────────────────────────────────────────


class _RoleChangePayload(BaseModel):
    """PATCH /cells/{cell_id}/members/{user_id} body. Single-field."""

    model_config = ConfigDict(extra="forbid")

    role_id: UUID


# ── dependency factories ──────────────────────────────────────────────────


def get_cell_service(
    db: AsyncSession = Depends(get_db),
) -> CellService:
    return CellService(db)


def get_cell_repo(
    db: AsyncSession = Depends(get_db),
) -> CellRepository:
    return CellRepository(db)


def _cell_to_out(cell: Cell) -> CellOut:
    """Map a Cell ORM row to its public projection.

    Done manually because `settings_jsonb` (column) → `settings` (DTO field).
    """
    return CellOut(
        id=cell.id,
        workspace_id=cell.workspace_id,
        slug=cell.slug,
        display_name=cell.display_name,
        vertical_template_slug=cell.vertical_template_slug,
        settings=cell.settings_jsonb or {},
        created_at=cell.created_at,
        updated_at=cell.updated_at,
        archived_at=cell.archived_at,
    )


# ── /workspaces/{workspace_id}/cells ─────────────────────────────────────


@workspace_cells_router.post(
    "",
    response_model=CellOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_cell(
    workspace_id: UUID,
    payload: CellCreate,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: CellService = Depends(get_cell_service),
) -> CellOut:
    try:
        cell = await service.provision_cell(
            workspace_id=workspace_id,
            slug=payload.slug,
            display_name=payload.display_name,
            vertical_template_slug=payload.vertical_template_slug,
            requested_by_user_id=auth.user.id,
            settings=payload.settings,
        )
    except IntegrityError as exc:
        raise CellSlugConflict() from exc
    return _cell_to_out(cell)


@workspace_cells_router.get(
    "",
    response_model=CellPage,
)
async def list_cells(
    workspace_id: UUID,
    limit: int = 50,
    cursor: str | None = None,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001
    repo: CellRepository = Depends(get_cell_repo),
) -> CellPage:
    cells = await repo.list_by_workspace(workspace_id=workspace_id, limit=limit, cursor=cursor)
    return CellPage(items=[_cell_to_out(c) for c in cells], next_cursor=None)


# ── /cells/{cell_id} ──────────────────────────────────────────────────────


@router.get(
    "/{cell_id}",
    response_model=CellOut,
)
async def get_cell(
    cell_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001
    repo: CellRepository = Depends(get_cell_repo),
) -> CellOut:
    cell = await repo.find_by_id(cell_id)
    if cell is None:
        raise CellNotFound()
    return _cell_to_out(cell)


# ── /cells/{cell_id}/members ──────────────────────────────────────────────


@router.get(
    "/{cell_id}/members",
    response_model=list[CellMemberOut],
)
async def list_members(
    cell_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001
    service: CellService = Depends(get_cell_service),
) -> list[CellMemberOut]:
    members = await service.list_members(cell_id=cell_id)
    return [CellMemberOut.model_validate(m) for m in members]


@router.post(
    "/{cell_id}/members/invite",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    cell_id: UUID,
    payload: InvitationCreate,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: CellService = Depends(get_cell_service),
) -> InvitationOut:
    invitation_id, expires_at = await service.invite_member(
        cell_id=cell_id,
        email=payload.email,
        role_id=payload.role_id,
        invited_by=auth.user.id,
    )
    return InvitationOut(
        id=invitation_id,
        cell_id=cell_id,
        email=payload.email,
        role_id=payload.role_id,
        expires_at=expires_at,
        created_at=expires_at,
    )


@router.patch(
    "/{cell_id}/members/{user_id}",
    response_model=CellMemberOut,
)
async def change_member_role(
    cell_id: UUID,
    user_id: UUID,
    payload: _RoleChangePayload,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: CellService = Depends(get_cell_service),
) -> CellMemberOut:
    member = await service.change_role(
        cell_id=cell_id,
        user_id=user_id,
        new_role_id=payload.role_id,
        changed_by=auth.user.id,
    )
    return CellMemberOut.model_validate(member)


@router.delete(
    "/{cell_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    cell_id: UUID,
    user_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: CellService = Depends(get_cell_service),
) -> Response:
    await service.remove_member(cell_id=cell_id, user_id=user_id, removed_by=auth.user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router", "workspace_cells_router"]
