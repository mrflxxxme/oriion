"""InProcessSSEPublisher — publish + subscribe + drain replay + sentinel exit."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from src.runtime.sse_events import TaskStreamEvent
from src.runtime.sse_publisher import (
    InProcessSSEPublisher,
    get_sse_publisher,
    reset_sse_publisher_for_tests,
)


@pytest.mark.asyncio
async def test_subscribe_replays_drained_events_before_subscription() -> None:
    """Late subscribers see ALL prior events via drain buffer."""
    pub = InProcessSSEPublisher()
    tid = uuid4()
    # Publish 3 events BEFORE any subscriber connects.
    for et in ["task.started", "task.step_started", "task.step_completed"]:
        await pub.publish(TaskStreamEvent(event_type=et, task_id=tid))
    # Now subscribe — must replay all 3.
    received: list[str] = []

    async def consume() -> None:
        async for ev in pub.subscribe(tid):
            received.append(ev.event_type)
            if ev.event_type == "task.step_completed":
                return

    await asyncio.wait_for(consume(), timeout=2.0)
    assert received == ["task.started", "task.step_started", "task.step_completed"]


@pytest.mark.asyncio
async def test_terminal_event_emits_sentinel_к_exit_subscribers() -> None:
    """task.completed inserts None sentinel; subscriber loop exits naturally."""
    pub = InProcessSSEPublisher()
    tid = uuid4()
    received: list[str] = []

    async def consume() -> None:
        async for ev in pub.subscribe(tid):
            received.append(ev.event_type)

    # Start subscriber so the queue exists when we publish.
    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await pub.publish(TaskStreamEvent(event_type="task.started", task_id=tid))
    await pub.publish(TaskStreamEvent(event_type="task.completed", task_id=tid))
    await asyncio.wait_for(consumer, timeout=2.0)
    assert received == ["task.started", "task.completed"]


@pytest.mark.asyncio
async def test_failed_event_also_emits_sentinel() -> None:
    pub = InProcessSSEPublisher()
    tid = uuid4()
    received: list[str] = []

    async def consume() -> None:
        async for ev in pub.subscribe(tid):
            received.append(ev.event_type)

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await pub.publish(TaskStreamEvent(event_type="task.failed", task_id=tid))
    await asyncio.wait_for(consumer, timeout=2.0)
    assert received == ["task.failed"]


@pytest.mark.asyncio
async def test_multiple_subscribers_each_receive_events() -> None:
    pub = InProcessSSEPublisher()
    tid = uuid4()
    received_a: list[str] = []
    received_b: list[str] = []

    async def consume(box: list[str]) -> None:
        async for ev in pub.subscribe(tid):
            box.append(ev.event_type)

    c1 = asyncio.create_task(consume(received_a))
    c2 = asyncio.create_task(consume(received_b))
    await asyncio.sleep(0.05)
    await pub.publish(TaskStreamEvent(event_type="task.started", task_id=tid))
    await pub.publish(TaskStreamEvent(event_type="task.completed", task_id=tid))
    await asyncio.wait_for(asyncio.gather(c1, c2), timeout=2.0)
    assert received_a == ["task.started", "task.completed"]
    assert received_b == ["task.started", "task.completed"]


@pytest.mark.asyncio
async def test_singleton_accessor() -> None:
    reset_sse_publisher_for_tests()
    pub1 = get_sse_publisher()
    pub2 = get_sse_publisher()
    assert pub1 is pub2


@pytest.mark.asyncio
async def test_reset_replaces_singleton() -> None:
    pub1 = get_sse_publisher()
    reset_sse_publisher_for_tests()
    pub2 = get_sse_publisher()
    assert pub1 is not pub2
