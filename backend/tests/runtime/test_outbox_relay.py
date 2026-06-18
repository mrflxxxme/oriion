"""Unit: transactional-outbox relay — at-least-once + idempotent (AC-W1-4)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from src.runtime.queue import outbox_relay
from src.runtime.queue.outbox_relay import (
    _publish_event,
    relay_outbox_batch,
    trigger_outbox_relay,
)
from src.tasks.models import OutboxEvent


def _event() -> OutboxEvent:
    ev = OutboxEvent(
        ce_type="oriion.tasks.created.v1",
        ce_source="oriion://contexts/tasks",
        data={"task_id": str(uuid4())},
    )
    ev.ce_id = uuid4()
    ev.published_at = None
    return ev


class _RelaySession:
    """Stub session: execute() returns the prepared unpublished events."""

    def __init__(self, events: list[OutboxEvent]) -> None:
        self._events = events
        self.commits = 0

    async def execute(self, _stmt: Any) -> Any:
        events = self._events

        class _Scalars:
            def all(self) -> list[OutboxEvent]:
                return list(events)

        class _Res:
            def scalars(self) -> Any:
                return _Scalars()

        return _Res()

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_relay_publishes_and_stamps_published_at() -> None:
    events = [_event(), _event()]
    session = _RelaySession(events)
    published: list[str] = []

    async def fake_publish(ev: OutboxEvent) -> None:
        published.append(str(ev.ce_id))

    count = await relay_outbox_batch(session, publish=fake_publish)  # type: ignore[arg-type]

    assert count == 2
    assert len(published) == 2
    assert all(e.published_at is not None for e in events)  # stamped
    assert session.commits == 1


@pytest.mark.asyncio
async def test_relay_at_least_once_leaves_row_unpublished_on_failure() -> None:
    """If publish fails, published_at is never stamped + the TX never commits,
    so the row is retried next run (at-least-once)."""
    events = [_event()]
    session = _RelaySession(events)

    async def boom(_ev: OutboxEvent) -> None:
        raise RuntimeError("downstream bus down")

    with pytest.raises(RuntimeError):
        await relay_outbox_batch(session, publish=boom)  # type: ignore[arg-type]

    assert events[0].published_at is None  # not marked → will be re-published
    assert session.commits == 0


@pytest.mark.asyncio
async def test_default_publisher_passes_stable_ce_id() -> None:
    ev = _event()
    with patch.object(outbox_relay, "emit_cloudevent", new=AsyncMock()) as emit:
        await _publish_event(ev)
    emit.assert_awaited_once()
    assert emit.await_args.kwargs["ce_id"] == str(ev.ce_id)
    assert emit.await_args.kwargs["ce_type"] == ev.ce_type


def test_trigger_outbox_relay_enqueues() -> None:
    # Root conftest sets DRAMATIQ_TESTING=1 → StubBroker, so .send() is a no-op
    # enqueue that must not raise.
    trigger_outbox_relay()
