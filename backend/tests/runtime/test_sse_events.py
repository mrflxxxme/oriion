"""SSE event types — TaskStreamEvent Pydantic shape."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.runtime.sse_events import TaskStreamEvent


def test_minimal_event_default_timestamp_and_payload() -> None:
    task_id = uuid4()
    ev = TaskStreamEvent(event_type="task.started", task_id=task_id)
    assert ev.event_type == "task.started"
    assert ev.task_id == task_id
    assert ev.payload == {}
    assert isinstance(ev.timestamp, datetime)


def test_full_event_with_payload() -> None:
    ts = datetime.now(UTC)
    ev = TaskStreamEvent(
        event_type="task.completed",
        task_id=uuid4(),
        timestamp=ts,
        payload={"total_cost_credits": "13.5", "artifacts": 3},
    )
    assert ev.timestamp == ts
    assert ev.payload["artifacts"] == 3


def test_invalid_event_type_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskStreamEvent(event_type="task.invented", task_id=uuid4())


def test_all_canonical_event_types_accepted() -> None:
    canonical = [
        "task.started",
        "task.step_started",
        "task.step_token",
        "task.step_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.completed",
        "task.cancelled",
        "task.failed",
    ]
    for et in canonical:
        ev = TaskStreamEvent(event_type=et, task_id=uuid4())
        assert ev.event_type == et


def test_event_serializes_к_dict() -> None:
    tid = uuid4()
    ev = TaskStreamEvent(event_type="task.started", task_id=tid, payload={"k": "v"})
    d = ev.model_dump(mode="json")
    assert d["event_type"] == "task.started"
    assert d["task_id"] == str(tid)
    assert d["payload"] == {"k": "v"}
