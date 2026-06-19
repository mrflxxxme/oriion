"""In-process SSE publisher with a Redis-pubsub-compatible interface.

Phase 00.5b Commit 6. Wave 0 uses an asyncio.Queue per task_id so the
demo-flow integration test (Commit 7) can subscribe synchronously and
assert event order deterministically. Wave 1 swaps the backing store to
Redis pub/sub without changing the SSEPublisher Protocol or call sites.

Pattern:
    pub = get_sse_publisher()
    await pub.publish(TaskStreamEvent(...))
    async for event in pub.subscribe(task_id):
        handle(event)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from src.runtime.sse_events import TaskStreamEvent


class SSEPublisher(Protocol):
    """Pub/sub interface — single instance lives on app.state."""

    async def publish(self, event: TaskStreamEvent) -> None: ...

    def subscribe(self, task_id: UUID) -> AsyncIterator[TaskStreamEvent]: ...


class InProcessSSEPublisher:
    """asyncio.Queue per task_id. Wave 0 demo-flow + CI tests."""

    def __init__(self) -> None:
        self._queues: dict[UUID, list[asyncio.Queue[TaskStreamEvent | None]]] = {}
        self._lock = asyncio.Lock()
        # Drain buffer per task — events published BEFORE a subscriber connects
        # are kept here and replayed at subscribe-time. Important for the demo
        # flow integration test which subscribes AFTER the orchestrator has
        # already emitted some events (otherwise the assert-order chain would
        # race the publish loop).
        self._drain: dict[UUID, list[TaskStreamEvent]] = {}
        # Track which tasks are completed so subscribers can exit cleanly.
        self._completed: set[UUID] = set()

    async def publish(self, event: TaskStreamEvent) -> None:
        async with self._lock:
            queues = self._queues.get(event.task_id, [])
            self._drain.setdefault(event.task_id, []).append(event)
            if event.event_type in {"task.completed", "task.cancelled", "task.failed"}:
                self._completed.add(event.task_id)
            for q in queues:
                await q.put(event)
                if event.task_id in self._completed:
                    await q.put(None)  # sentinel for subscribers to exit

    async def subscribe(self, task_id: UUID) -> AsyncIterator[TaskStreamEvent]:
        queue: asyncio.Queue[TaskStreamEvent | None] = asyncio.Queue()
        async with self._lock:
            self._queues.setdefault(task_id, []).append(queue)
            # Replay drain so late subscribers see the full event log.
            for past in self._drain.get(task_id, []):
                await queue.put(past)
            if task_id in self._completed:
                await queue.put(None)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    return
                yield event
        finally:
            async with self._lock:
                self._queues.get(task_id, []).remove(queue)


_singleton: SSEPublisher | None = None


def get_sse_publisher() -> SSEPublisher:
    """Process-wide singleton accessor. Backend is chosen by Settings.sse_backend:
    'inprocess' (default — deterministic CI + single-worker dev) keeps the
    asyncio.Queue publisher; 'redis' selects the Redis-Streams publisher so events
    cross process boundaries (out-of-process Dramatiq worker + gunicorn -w >1).
    Tests can monkeypatch by binding a fresh publisher to the module attribute."""
    global _singleton
    if _singleton is None:
        from src._shared.config import get_settings

        settings = get_settings()
        if settings.sse_backend == "redis":
            from src.runtime.redis_sse_publisher import RedisSSEPublisher

            _singleton = RedisSSEPublisher(
                redis_url=settings.redis_url.get_secret_value(),
                poll_fallback=settings.sse_redis_poll_fallback,
            )
        else:
            _singleton = InProcessSSEPublisher()
    return _singleton


def reset_sse_publisher_for_tests() -> None:
    """Reset the singleton — test fixtures call this between scenarios so
    drained event logs don't leak across cases."""
    global _singleton
    _singleton = InProcessSSEPublisher()
