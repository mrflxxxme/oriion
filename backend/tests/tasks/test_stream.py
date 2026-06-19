"""``stream_task_events`` — SSE frame generator with keep-alive heartbeats.

The Redis publisher blocks on XREAD while the worker is still generating, so the
``/stream`` server is silent until the first event. These tests pin the three
behaviours that keep that silence from breaking the client: events pass through
and the terminal ends the stream; a long silence emits an SSE keep-alive comment
WITHOUT cancelling the (blocking) subscription; and a subscription failure is
logged + ends the stream cleanly instead of leaking an unhandled exception that
the client only sees as a truncated response.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from src.runtime.sse_events import TaskStreamEvent
from src.tasks.routers import stream as stream_router
from src.tasks.routers.stream import stream_task_events


class _FakePublisher:
    """Drives ``subscribe`` from a scripted event list, with an optional pre-yield
    delay (to simulate a silent XREAD window) and an optional raise (Redis down)."""

    def __init__(
        self,
        events: list[TaskStreamEvent],
        *,
        pre_delay: float = 0.0,
        raise_exc: Exception | None = None,
    ) -> None:
        self._events = events
        self._pre_delay = pre_delay
        self._raise_exc = raise_exc

    async def publish(self, event: TaskStreamEvent) -> None:  # pragma: no cover - unused
        raise NotImplementedError

    async def subscribe(self, task_id: UUID) -> AsyncIterator[TaskStreamEvent]:
        if self._pre_delay:
            await asyncio.sleep(self._pre_delay)
        if self._raise_exc is not None:
            raise self._raise_exc
        for event in self._events:
            yield event


async def _collect(gen: AsyncIterator[str], *, timeout: float = 2.0) -> list[str]:
    """Drain a frame generator to exhaustion under a safety timeout so a
    regression that fails to terminate surfaces as a test failure, not a hang."""

    async def _run() -> list[str]:
        return [frame async for frame in gen]

    return await asyncio.wait_for(_run(), timeout)


@pytest.mark.asyncio
async def test_passes_events_through_and_terminal_ends_stream() -> None:
    tid = uuid4()
    events = [
        TaskStreamEvent(event_type="task.started", task_id=tid),
        TaskStreamEvent(event_type="task.completed", task_id=tid, payload={"summary": "done"}),
    ]
    frames = await _collect(stream_task_events(_FakePublisher(events), tid))

    assert frames == [
        "event: task.started\ndata: {}\n\n",
        'event: task.completed\ndata: {"summary":"done"}\n\n',
    ]


@pytest.mark.asyncio
async def test_emits_keepalive_during_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    """A silent window longer than the heartbeat interval yields a keep-alive
    comment, then the real event still arrives (the blocking subscription is not
    cancelled to inject the heartbeat)."""
    monkeypatch.setattr(stream_router, "_SSE_HEARTBEAT_SECONDS", 0.02)
    tid = uuid4()
    events = [TaskStreamEvent(event_type="task.completed", task_id=tid)]
    publisher = _FakePublisher(events, pre_delay=0.1)  # silent past several heartbeats

    frames = await _collect(stream_task_events(publisher, tid))

    assert stream_router._SSE_KEEPALIVE_FRAME in frames
    # The keep-alive(s) precede the terminal event, and the event still lands.
    assert frames[-1] == "event: task.completed\ndata: {}\n\n"
    assert frames.index(stream_router._SSE_KEEPALIVE_FRAME) < len(frames) - 1


@pytest.mark.asyncio
async def test_subscribe_failure_is_logged_and_ends_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subscription error (e.g. Redis unreachable) must not propagate out of the
    generator — it is logged server-side and the stream ends via the sentinel."""
    logged: list[str] = []

    class _RecordingLogger:
        def exception(self, event: str, **_: object) -> None:
            logged.append(event)

    monkeypatch.setattr(stream_router, "logger", _RecordingLogger())
    tid = uuid4()
    publisher = _FakePublisher([], raise_exc=ConnectionError("redis down"))

    frames = await _collect(stream_task_events(publisher, tid))

    assert frames == []  # clean end, no partial frames, no raised exception
    assert logged == ["sse_stream_subscribe_failed"]
