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
    schedule_next_relay,
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
async def test_relay_at_least_once_leaves_failed_row_unpublished() -> None:
    """A failing publish leaves its row unpublished (retried next run) WITHOUT
    raising out of the batch — the row is isolated, the batch still commits."""
    events = [_event()]
    session = _RelaySession(events)

    async def boom(_ev: OutboxEvent) -> None:
        raise RuntimeError("downstream bus down")

    count = await relay_outbox_batch(session, publish=boom)  # type: ignore[arg-type]

    assert count == 0
    assert events[0].published_at is None  # not marked → will be re-published
    assert session.commits == 1  # batch still commits (nothing to stamp here)


@pytest.mark.asyncio
async def test_relay_isolates_poison_row_without_blocking_siblings() -> None:
    """One failing ("poison") row must NOT roll back the rows published before it
    (no duplicate storm) nor block the rows after it (no head-of-line starvation):
    the good rows are stamped + committed, only the poison row stays unpublished."""
    good_a, poison, good_b = _event(), _event(), _event()
    session = _RelaySession([good_a, poison, good_b])
    poison_id = str(poison.ce_id)

    async def selective(ev: OutboxEvent) -> None:
        if str(ev.ce_id) == poison_id:
            raise RuntimeError("this row always fails")

    count = await relay_outbox_batch(session, publish=selective)  # type: ignore[arg-type]

    assert count == 2  # both good rows published despite the poison in the middle
    assert good_a.published_at is not None
    assert good_b.published_at is not None  # row AFTER the poison still drained
    assert poison.published_at is None  # poison isolated → retried next run
    assert session.commits == 1


def test_safe_error_redacts_dsn_credentials() -> None:
    # A connection error carrying a DSN must not leak the password into logs.
    exc = RuntimeError("could not connect: postgresql+asyncpg://oriion:s3cr3t@db.host:5432/oriion")
    redacted = outbox_relay._safe_error(exc)
    assert "s3cr3t" not in redacted
    assert "oriion:s3cr3t@" not in redacted
    assert "://<redacted>@db.host:5432/oriion" in redacted


@pytest.mark.asyncio
async def test_default_publisher_passes_stable_ce_id() -> None:
    ev = _event()
    with patch.object(outbox_relay, "emit_cloudevent", new=AsyncMock()) as emit:
        await _publish_event(ev)
    emit.assert_awaited_once()
    assert emit.await_args.kwargs["ce_id"] == str(ev.ce_id)
    assert emit.await_args.kwargs["ce_type"] == ev.ce_type


def test_trigger_outbox_relay_nudges_without_forking_a_chain() -> None:
    # A nudge must send periodic=False so the one-shot run does NOT re-arm a
    # second perpetual self-reschedule chain (only the boot chain re-arms).
    with patch.object(outbox_relay.relay_outbox_actor, "send") as send:
        trigger_outbox_relay()
    send.assert_called_once_with(periodic=False)


def test_schedule_next_relay_enqueues_delayed() -> None:
    # The self-reschedule that makes the actor a periodic drain (ADR-036):
    # send_with_options(delay=...) — the periodic chain re-arms with the default
    # periodic=True (no kwargs), so each tick schedules exactly one successor.
    with patch.object(outbox_relay.relay_outbox_actor, "send_with_options") as swo:
        schedule_next_relay()
    swo.assert_called_once()
    assert swo.call_args.kwargs.get("delay") == outbox_relay.OUTBOX_RELAY_INTERVAL_MS
