"""POST/GET /api/v1/cells/{cell_id}/tasks — task CRUD + async dispatch."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import get_tenant_db_session
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.runtime.queue.actor import dispatch_task_actor
from src.tasks.exceptions import TaskNotDispatchable
from src.tasks.schemas import TaskCreateRequest, TaskOut
from src.tasks.services.task_service import TaskService

router = APIRouter(prefix="/cells/{cell_id}/tasks", tags=["tasks"])


def get_task_service(db: AsyncSession = Depends(get_tenant_db_session)) -> TaskService:
    """F-SEC-H1 fix: tenant-scoped session so FORCE-RLS on tasks.tasks
    passes WITH CHECK on INSERT + filters on SELECT under oriion_app."""
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


@router.post("/{task_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_task(
    cell_id: UUID,
    task_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    db: AsyncSession = Depends(get_tenant_db_session),
) -> dict[str, object]:
    """Async dispatch (AC-W1-16a): enqueue a Dramatiq actor and return 202 in
    <1s instead of blocking the request thread for the whole orchestration.

    The worker runs the researcher→analyst→writer orchestration off-request and
    streams its SSE ledger through the Redis-Streams publisher (AC-W1-1), so the
    caller watches progress + reads the result via GET /stream (the
    ``task.completed`` event carries the CoordinatorOutput). This endpoint no
    longer returns ``result`` — a deliberate contract change (ADR-034).

    Commit-then-enqueue: ``dispatched_at`` is persisted before ``.send`` so a
    crash strands the task as queued (recoverable) rather than risking a worker
    reading a rolled-back row; the worker guards on ``status=='queued'`` so a
    redelivered message is a no-op. The full transactional outbox is AC-W1-4.
    """
    _ = cell_id  # routing scope — RLS enforces tenant at the DB layer
    task = await service.get_task(task_id)  # raises TaskNotFound → 404
    if task.status != "queued":
        raise TaskNotDispatchable(f"task {task_id} status={task.status!r}, expected 'queued'")

    task.dispatched_at = datetime.now(UTC)
    await db.commit()
    dispatch_task_actor.send(str(task_id), str(auth.user.id))
    return {
        "task_id": str(task_id),
        "status": "dispatched",
    }


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
