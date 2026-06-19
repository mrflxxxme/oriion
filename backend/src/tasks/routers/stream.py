"""GET /api/v1/cells/{cell_id}/tasks/{task_id}/stream — SSE stream.

Wave 0 implementation: subscribes to the runtime SSE publisher in-process.
A full Redis-pubsub bridge for multi-worker SSE lands in Wave 1+; until
then the publisher uses an in-process broker so the demo flow integration
test (Commit 7) can assert event ordering deterministically.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Final
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.iam.middleware import AuthenticatedUser, get_current_user
from src.runtime.sse_events import TaskStreamEvent
from src.runtime.sse_publisher import SSEPublisher, get_sse_publisher
from src.tasks.routers.tasks import get_task_service
from src.tasks.services.task_service import TaskService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/cells/{cell_id}/tasks/{task_id}/stream", tags=["tasks"])

# Emit an SSE keep-alive comment after this much subscriber silence. The Redis
# publisher blocks on XREAD while the worker is still generating, so the server
# is silent between events (and fully silent until the first one). A long silence
# trips the client's per-read timeout and lets idle proxies drop the stream — the
# comment keeps bytes flowing. Must stay well under the client read timeout (300s)
# and the Redis XREAD block window (5s), so 15s gives a wide margin both ways.
_SSE_HEARTBEAT_SECONDS: Final = 15.0
# SSE comment line (starts with ':') — ignored by every conformant SSE client.
_SSE_KEEPALIVE_FRAME: Final = ": keep-alive\n\n"


def _format_sse_event(event_type: str, payload: dict[str, object]) -> str:
    body = json.dumps(payload, default=str, separators=(",", ":"))
    return f"event: {event_type}\ndata: {body}\n\n"


async def stream_task_events(publisher: SSEPublisher, task_id: UUID) -> AsyncIterator[str]:
    """Yield SSE frames for ``task_id``, interleaving keep-alive comments during
    the silent XREAD windows so an initially-silent or long-running generation
    keeps the HTTP connection warm (no client read-timeout, no idle-proxy drop).

    The subscription's blocking XREAD must NOT be cancelled to inject a heartbeat
    — cancelling it would finalize the underlying async generator and close its
    dedicated Redis client mid-stream. So the subscription runs in a pump task
    that feeds a queue, and this coroutine races ``queue.get()`` against the
    heartbeat interval. A subscription failure (e.g. Redis unreachable) is logged
    server-side and ends the stream cleanly via the sentinel, instead of leaking
    an unhandled exception that the client only sees as a truncated response.
    """
    queue: asyncio.Queue[TaskStreamEvent | None] = asyncio.Queue()

    async def _pump() -> None:
        try:
            async for event in publisher.subscribe(task_id):
                await queue.put(event)
        except Exception:  # surface infra failure (e.g. Redis down), don't truncate silently
            logger.exception("sse_stream_subscribe_failed", task_id=str(task_id))
        finally:
            await queue.put(None)  # sentinel: subscription ended (clean OR errored)

    pump = asyncio.create_task(_pump())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), _SSE_HEARTBEAT_SECONDS)
            except TimeoutError:
                yield _SSE_KEEPALIVE_FRAME
                continue
            if event is None:
                return
            yield _format_sse_event(event.event_type, event.payload)
    finally:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump


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
    return StreamingResponse(stream_task_events(publisher, task_id), media_type="text/event-stream")
