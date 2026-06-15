"""RedisSSEPublisher — cross-process drain-replay + live delivery (AC-W1-1).

Two RedisSSEPublisher instances share ONE fakeredis server to simulate the
worker process (publisher) and the web process (/stream subscriber). Uses the
poll fallback so the suite never depends on fakeredis XREAD BLOCK semantics.
"""

from __future__ import annotations

import asyncio
from typing import cast
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis, FakeServer
from redis.asyncio import Redis
from src.runtime.redis_sse_publisher import RedisSSEPublisher
from src.runtime.sse_events import TaskStreamEvent

_LEDGER = [
    "task.started",
    "task.delegation_started",
    "task.delegation_completed",
    "task.completed",
]


def _publisher(server: FakeServer) -> RedisSSEPublisher:
    client = cast(Redis, FakeAsyncRedis(server=server, decode_responses=True))
    return RedisSSEPublisher(client=client, poll_fallback=True)


@pytest.mark.asyncio
async def test_cross_process_drain_replay() -> None:
    """Subscriber on a SECOND publisher (shared server) connecting AFTER the task
    completed replays the whole ledger in order, then exits on the terminal."""
    server = FakeServer()
    worker = _publisher(server)  # "worker process" — produces events
    web = _publisher(server)  # "web process" — serves /stream
    tid = uuid4()

    for et in _LEDGER:
        await worker.publish(TaskStreamEvent(event_type=et, task_id=tid))

    received: list[str] = []

    async def consume() -> None:
        async for ev in web.subscribe(tid):
            received.append(ev.event_type)

    await asyncio.wait_for(consume(), timeout=3.0)
    assert received == _LEDGER


@pytest.mark.asyncio
async def test_cross_process_live_delivery() -> None:
    """A subscriber that connects BEFORE the terminal event receives events live
    as the other process publishes them."""
    server = FakeServer()
    worker = _publisher(server)
    web = _publisher(server)
    tid = uuid4()
    received: list[str] = []

    async def consume() -> None:
        async for ev in web.subscribe(tid):
            received.append(ev.event_type)

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await worker.publish(TaskStreamEvent(event_type="task.started", task_id=tid))
    await worker.publish(TaskStreamEvent(event_type="task.completed", task_id=tid))
    await asyncio.wait_for(consumer, timeout=3.0)
    assert received == ["task.started", "task.completed"]


@pytest.mark.asyncio
async def test_failed_terminal_exits_cleanly() -> None:
    server = FakeServer()
    pub = _publisher(server)
    tid = uuid4()
    await pub.publish(TaskStreamEvent(event_type="task.started", task_id=tid))
    await pub.publish(TaskStreamEvent(event_type="task.failed", task_id=tid))

    received: list[str] = []

    async def consume() -> None:
        async for ev in pub.subscribe(tid):
            received.append(ev.event_type)

    await asyncio.wait_for(consume(), timeout=3.0)
    assert received == ["task.started", "task.failed"]


@pytest.mark.asyncio
async def test_event_payload_round_trips() -> None:
    server = FakeServer()
    pub = _publisher(server)
    tid = uuid4()
    await pub.publish(
        TaskStreamEvent(
            event_type="task.completed",
            task_id=tid,
            payload={"total_cost_credits": "22.9", "total_duration_ms": 163000},
        )
    )
    got: list[TaskStreamEvent] = []
    async for ev in pub.subscribe(tid):
        got.append(ev)
    assert len(got) == 1
    assert got[0].task_id == tid
    assert got[0].payload["total_duration_ms"] == 163000


def test_requires_client_or_url() -> None:
    with pytest.raises(ValueError, match="client or a redis_url"):
        RedisSSEPublisher()
