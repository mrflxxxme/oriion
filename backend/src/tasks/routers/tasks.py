"""POST/GET /api/v1/cells/{cell_id}/tasks — task CRUD."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.tasks.schemas import TaskCreateRequest, TaskOut
from src.tasks.services.task_service import TaskService

router = APIRouter(prefix="/cells/{cell_id}/tasks", tags=["tasks"])


def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)


@router.post("", response_model=TaskOut, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    cell_id: UUID,
    payload: TaskCreateRequest,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskOut:
    """Create a new task. Status starts at 'queued'; the runtime orchestrator
    (Commit 6) picks it up and transitions to 'running'."""
    task = await service.create_task(
        cell_id=cell_id,
        user_id=auth.user.id,
        title=payload.title,
        description=payload.description,
        prompt=payload.prompt,
        parent_task_id=payload.parent_task_id,
    )
    return TaskOut.model_validate(task)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    cell_id: UUID,
    task_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001
    service: TaskService = Depends(get_task_service),
) -> TaskOut:
    """Read a single task. cell_id in path is the routing scope —
    actual RLS filtering happens at the DB layer via app.current_cell_id GUC."""
    _ = cell_id
    task = await service.get_task(task_id)
    return TaskOut.model_validate(task)


@router.post("/{task_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_task(
    cell_id: UUID,
    task_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001
    service: TaskService = Depends(get_task_service),
) -> dict[str, object]:
    """Cancel a task + cascade to all descendants atomically (AC12)."""
    _ = cell_id
    descendants = await service.cancel_task(task_id)
    return {
        "task_id": str(task_id),
        "status": "cancelled",
        "cascaded_to": [str(t) for t in descendants],
    }
