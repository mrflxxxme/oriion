"""Redis-Streams SSE publisher — cross-process drain-replay (AC-W1-1).

The Wave-0 ``InProcessSSEPublisher`` keeps an asyncio.Queue per task_id, which
only works when the event producer (the orchestrator) and the ``/stream``
subscriber live in the SAME process. Once dispatch moves onto an out-of-process
Dramatiq worker (AC-W1-16a) and the web tier scales to ``gunicorn -w >1``, the
producer and subscriber are in DIFFERENT processes — so we need a shared broker.

**Why Redis Streams, not pub/sub:** plain pub/sub drops messages for subscribers
that connect *after* publish, which would break the drain-replay contract the
demo harness + frontend rely on (a ``/stream`` GET issued after the task already
finished must still replay the whole ledger). A Stream persists the per-task log,
so a late subscriber ``XREAD``s from id ``0`` (full replay) then blocks for new
entries. The terminal event (``task.completed`` / ``cancelled`` / ``failed``) is
the sentinel that ends the subscription — it is always in the Stream history, so
even a subscriber that connects post-completion sees it and exits cleanly.

This implements the same ``SSEPublisher`` Protocol as ``InProcessSSEPublisher``;
``get_sse_publisher()`` selects between them via ``Settings.sse_backend``, so all
call sites (orchestrator publish, ``/stream`` subscribe) are unchanged.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Final, cast
from uuid import UUID

import structlog
from redis.asyncio import Redis

from src.runtime.sse_events import TaskStreamEvent

logger = structlog.get_logger(__name__)

_TERMINAL_EVENTS: Final[frozenset[str]] = frozenset(
    {"task.completed", "task.cancelled", "task.failed"}
)
_DEFAULT_STREAM_TTL_SECONDS: Final = 3600  # 1h — generous vs the ~163s generation
_DEFAULT_BLOCK_MS: Final = 5000
_DEFAULT_POLL_INTERVAL_SECONDS: Final = 0.05


def _stream_key(task_id: UUID) -> str:
    return f"task:stream:{task_id}"


def _extract_data(fields: dict[Any, Any]) -> str | None:
    """Pull the JSON payload out of an XREAD entry, tolerating bytes-or-str keys
    (a client built with ``decode_responses=False`` returns bytes)."""
    raw = fields.get("data")
    if raw is None:
        raw = fields.get(b"data")
    if raw is None:
        return None
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)


class RedisSSEPublisher:
    """Redis-Streams-backed SSE publisher (same Protocol as InProcess).

    Either inject a ready ``client`` (tests share one fakeredis server between
    two publisher instances to simulate worker+web processes) or pass a
    ``redis_url`` (production): ``publish`` reuses one shared client, while each
    ``subscribe`` generator gets its own dedicated client because a blocking
    ``XREAD`` monopolises a connection for the block window.
    """

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        client: Redis | None = None,
        poll_fallback: bool = False,
        block_ms: int = _DEFAULT_BLOCK_MS,
        poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
        stream_ttl_seconds: int = _DEFAULT_STREAM_TTL_SECONDS,
    ) -> None:
        if client is None and redis_url is None:
            raise ValueError("RedisSSEPublisher needs either a client or a redis_url")
        self._redis_url = redis_url
        self._injected_client = client
        self._shared_client: Redis | None = client
        self._poll_fallback = poll_fallback
        self._block_ms = block_ms
        self._poll_interval = poll_interval_seconds
        self._stream_ttl = stream_ttl_seconds

    def _make_client(self) -> Redis:
        """A dedicated client (production path). Tests inject a client instead."""
        if self._redis_url is None:
            raise RuntimeError("RedisSSEPublisher._make_client requires a redis_url")
        # redis-py's from_url is typed as Any → cast at the boundary (same as
        # _shared/db/redis.get_redis_client).
        return cast(Redis, Redis.from_url(self._redis_url, encoding="utf-8", decode_responses=True))

    def _publish_client(self) -> Redis:
        if self._shared_client is None:
            self._shared_client = self._make_client()
        return self._shared_client

    async def publish(self, event: TaskStreamEvent) -> None:
        client = self._publish_client()
        key = _stream_key(event.task_id)
        await client.xadd(key, {"data": event.model_dump_json()})
        # Refresh the TTL on every append so the Stream survives for the full
        # task lifetime + a replay window, then self-cleans.
        await client.expire(key, self._stream_ttl)

    async def aclose(self) -> None:
        """Close the lazily-created shared publish client.

        Required by the Dramatiq worker, which builds a fresh publisher per
        message (per-loop) and must release the redis connection at message end
        so it never outlives its ``asyncio.run`` loop (the cross-loop reuse that
        raises ``Event loop is closed`` on the 2nd message). No-op for an
        injected client — the test owns that lifecycle.
        """
        if self._injected_client is None and self._shared_client is not None:
            await self._shared_client.aclose()
            self._shared_client = None

    async def subscribe(self, task_id: UUID) -> AsyncIterator[TaskStreamEvent]:
        key = _stream_key(task_id)
        # Dedicated client per generator in production; reuse the injected one
        # in tests (single fakeredis server, no real connection to monopolise).
        owns_client = self._injected_client is None
        client = self._injected_client if self._injected_client is not None else self._make_client()
        last_id = "0"
        try:
            while True:
                if self._poll_fallback:
                    streams = await client.xread({key: last_id})
                    if not streams:
                        await asyncio.sleep(self._poll_interval)
                        continue
                else:
                    streams = await client.xread({key: last_id}, block=self._block_ms)
                    if not streams:
                        continue
                for _stream_name, entries in streams:
                    for entry_id, fields in entries:
                        last_id = entry_id
                        data = _extract_data(fields)
                        if data is None:
                            continue
                        event = TaskStreamEvent.model_validate_json(data)
                        yield event
                        if event.event_type in _TERMINAL_EVENTS:
                            return
        finally:
            if owns_client:
                await client.aclose()
