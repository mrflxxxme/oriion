"""Memory API — cell + role memory CRUD + similarity search (ADR-011 Wave-1).

Cell scope comes from the RLS tenant context (``get_current_cell_id``), NOT a
path param — Wave-0 single-cell, RLS-authoritative (mirrors billing). The ADR's
``/cells/<id>/...`` shape lands with multi-cell membership. A manual ``POST`` is
the explicit «запомни». A soft-cap breach is advisory: the entry is still
stored and the ``X-Memory-Soft-Cap-Exceeded: true`` response header is set.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from src._shared.middleware.tenant_context import (
    get_current_cell_id,
    get_current_workspace_id,
)
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.memory.deps import get_cell_memory_service, get_role_memory_service
from src.memory.schemas import (
    MemoryEntryCreate,
    MemoryEntryOut,
    MemorySearchHit,
    RoleMemoryEntryCreate,
    RoleMemoryEntryOut,
    RoleMemorySearchHit,
)
from src.memory.services.memory_service import CellMemoryService
from src.memory.services.role_memory_service import RoleMemoryService

router = APIRouter(prefix="/memory", tags=["memory"])

_SOFT_CAP_HEADER = "X-Memory-Soft-Cap-Exceeded"


# ── cell memory ─────────────────────────────────────────────────────────── #


@router.get("", response_model=list[MemoryEntryOut])
async def list_cell_memory(
    svc: CellMemoryService = Depends(get_cell_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[MemoryEntryOut]:
    rows = await svc.list_recent(cell_id=cell_id, limit=limit, offset=offset)
    return [MemoryEntryOut.model_validate(row) for row in rows]


@router.get("/search", response_model=list[MemorySearchHit])
async def search_cell_memory(
    q: str = Query(min_length=1, max_length=2000),
    svc: CellMemoryService = Depends(get_cell_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[MemorySearchHit]:
    hits = await svc.search(cell_id=cell_id, query=q, limit=limit)
    return [
        MemorySearchHit(entry=MemoryEntryOut.model_validate(entry), score=score)
        for entry, score in hits
    ]


@router.post("", response_model=MemoryEntryOut, status_code=status.HTTP_201_CREATED)
async def add_cell_memory(
    payload: MemoryEntryCreate,
    response: Response,
    svc: CellMemoryService = Depends(get_cell_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
    workspace_id: UUID = Depends(get_current_workspace_id),
    auth: AuthenticatedUser = Depends(get_current_user),
) -> MemoryEntryOut:
    entry, soft_cap_exceeded = await svc.add(
        cell_id=cell_id,
        workspace_id=workspace_id,
        content=payload.content,
        kind=payload.kind,
        title=payload.title,
        tags=payload.tags,
        contains_pii=payload.contains_pii,
        created_by_user_id=auth.user.id,
    )
    if soft_cap_exceeded:
        response.headers[_SOFT_CAP_HEADER] = "true"
    return MemoryEntryOut.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cell_memory(
    entry_id: UUID,
    svc: CellMemoryService = Depends(get_cell_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> None:
    await svc.delete(cell_id=cell_id, entry_id=entry_id)


# ── role memory (per agent-instance) ────────────────────────────────────── #


@router.get("/agents/{agent_id}", response_model=list[RoleMemoryEntryOut])
async def list_role_memory(
    agent_id: UUID,
    svc: RoleMemoryService = Depends(get_role_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[RoleMemoryEntryOut]:
    rows = await svc.list_recent(cell_id=cell_id, agent_id=agent_id, limit=limit, offset=offset)
    return [RoleMemoryEntryOut.model_validate(row) for row in rows]


@router.get("/agents/{agent_id}/search", response_model=list[RoleMemorySearchHit])
async def search_role_memory(
    agent_id: UUID,
    q: str = Query(min_length=1, max_length=2000),
    svc: RoleMemoryService = Depends(get_role_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[RoleMemorySearchHit]:
    hits = await svc.search(cell_id=cell_id, agent_id=agent_id, query=q, limit=limit)
    return [
        RoleMemorySearchHit(entry=RoleMemoryEntryOut.model_validate(entry), score=score)
        for entry, score in hits
    ]


@router.post(
    "/agents/{agent_id}",
    response_model=RoleMemoryEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_role_memory(
    agent_id: UUID,
    payload: RoleMemoryEntryCreate,
    response: Response,
    svc: RoleMemoryService = Depends(get_role_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
    workspace_id: UUID = Depends(get_current_workspace_id),
    auth: AuthenticatedUser = Depends(get_current_user),
) -> RoleMemoryEntryOut:
    entry, soft_cap_exceeded = await svc.add(
        cell_id=cell_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        content=payload.content,
        kind=payload.kind,
        title=payload.title,
        tags=payload.tags,
        contains_pii=payload.contains_pii,
        created_by_user_id=auth.user.id,
    )
    if soft_cap_exceeded:
        response.headers[_SOFT_CAP_HEADER] = "true"
    return RoleMemoryEntryOut.model_validate(entry)


@router.delete("/agents/{agent_id}/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_memory(
    agent_id: UUID,
    entry_id: UUID,
    svc: RoleMemoryService = Depends(get_role_memory_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> None:
    await svc.delete(cell_id=cell_id, agent_id=agent_id, entry_id=entry_id)
