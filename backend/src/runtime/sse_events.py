"""SSE event types for /api/v1/cells/{cell_id}/tasks/{task_id}/stream."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TaskStreamEventType = Literal[
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


class TaskStreamEvent(BaseModel):
    """SSE payload emitted to /stream subscribers.

    Per contracts/tasks/events.yaml event types — UI consumes for Phase 00.7
    frontend. payload schema is event-type-specific.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_type: TaskStreamEventType
    task_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
