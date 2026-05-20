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

router = APIRouter(prefix="/cells/{cell_id}/tasks/{task_id}/stream", tags=["tasks"])


def _format_sse_event(event_type: str, payload: dict[str, object]) -> str:
    body = json.dumps(payload, default=str, separators=(",", ":"))
    return f"event: {event_type}\ndata: {body}\n\n"


@router.get("", response_class=StreamingResponse)
async def stream_task(
    cell_id: UUID,
    task_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),  # noqa: ARG001 — auth required
) -> StreamingResponse:
    """SSE endpoint — yields per-step events as the orchestrator runs."""
    _ = cell_id
    publisher = get_sse_publisher()

    async def gen() -> AsyncIterator[str]:
        async for event in publisher.subscribe(task_id):
            yield _format_sse_event(event.event_type, event.payload)

    return StreamingResponse(gen(), media_type="text/event-stream")
