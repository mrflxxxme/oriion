"""POST/GET /api/v1/cells/{cell_id}/tasks — task CRUD + inline dispatch."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import get_tenant_db_session
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.llm_gateway.deps import get_llm_router
from src.runtime.dispatch import dispatch_task
from src.runtime.sse_publisher import get_sse_publisher
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
    request: Request,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001
    service: TaskService = Depends(get_task_service),
    db: AsyncSession = Depends(get_tenant_db_session),
) -> dict[str, object]:
    """Inline orchestrator-dispatch (Phase 00.6 PR-B — closes the PR-A
    CRITICAL FINDING: POST /tasks created a queued row but never dispatched).

    Synchronously runs the Wave-0 deterministic researcher→analyst→writer
    pipeline against the queued task — each specialist is a real LLM call
    through LLMRouter. The orchestrator emits the full SSE ledger to the
    in-process publisher, so a concurrent (or subsequent, via drain-replay)
    GET /stream subscriber sees task.started -> 3x delegation -> task.completed.

    Blocks until orchestration finishes (workers=1 invariant per F-ARC-H2).
    AC-W1-16 swaps this for a Dramatiq actor (return 202 immediately) + the
    real LLM-driven Coordinator once the model adapter forwards tool-calls.
    """
    _ = cell_id  # routing scope — RLS enforces tenant at the DB layer
    task = await service.get_task(task_id)  # raises TaskNotFound → 404
    if task.status != "queued":
        raise TaskNotDispatchable(f"task {task_id} status={task.status!r}, expected 'queued'")

    llm_router = get_llm_router(request)
    publisher = get_sse_publisher()
    try:
        result = await dispatch_task(
            task=task,
            session=db,
            llm_router=llm_router,
            sse_publisher=publisher,
        )
    except Exception:
        # F-CR-2 fix: the orchestrator writes task.status='failed' +
        # completed_at + cost on the session before re-raising. Without this
        # commit, get_db's rollback-on-exception would DISCARD that write —
        # leaving the row 'queued' while the SSE ledger says 'failed'
        # (DB/stream divergence + lost failure audit trail). Persist the
        # failed-state write, then re-raise so the RFC-7807 handler still runs.
        # AC-W1-16 (Dramatiq actor) gives each dispatch its own TX boundary.
        await db.commit()
        raise
    await db.commit()
    return {
        "task_id": str(task_id),
        "status": task.status,
        "result": result,
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
