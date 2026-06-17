"""GET /api/v1/cells/{cell_id}/tasks/{task_id}/stream — SSE stream.

Wave 0 implementation: subscribes to the runtime SSE publisher in-process.
A full Redis-pubsub bridge for multi-worker SSE lands in Wave 1+; until
then the publisher uses an in-process broker so the demo flow integration
test (Commit 7) can assert event ordering deterministically.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.iam.middleware import AuthenticatedUser, get_current_user
from src.runtime.sse_publisher import get_sse_publisher
from src.tasks.routers.tasks import get_task_service
from src.tasks.services.task_service import TaskService

router = APIRouter(prefix="/cells/{cell_id}/tasks/{task_id}/stream", tags=["tasks"])


def _format_sse_event(event_type: str, payload: dict[str, object]) -> str:
    body = json.dumps(payload, default=str, separators=(",", ":"))
    return f"event: {event_type}\ndata: {body}\n\n"


@router.get("", response_class=StreamingResponse)
async def stream_task(
    cell_id: UUID,
    task_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001 — auth required
    service: TaskService = Depends(get_task_service),
) -> StreamingResponse:
    """SSE endpoint — yields per-step events as the orchestrator runs.

    F-SEC IDOR fix: confirm the task is visible to the caller's tenant BEFORE
    subscribing. ``get_task_service`` depends on ``get_tenant_db_session`` (the
    same 3-GUC RLS path the sibling GET /tasks/{id} endpoint uses), so a
    foreign/unknown task_id is filtered by RLS → ``get_task`` raises
    ``TaskNotFound`` → 404, and the caller never reaches another tenant's
    ledger (``task.completed`` carries the full CoordinatorOutput).
    """
    _ = cell_id
    await service.get_task(task_id)  # raises TaskNotFound → 404 when RLS hides it
    publisher = get_sse_publisher()

    async def gen() -> AsyncIterator[str]:
        async for event in publisher.subscribe(task_id):
            yield _format_sse_event(event.event_type, event.payload)

    return StreamingResponse(gen(), media_type="text/event-stream")
