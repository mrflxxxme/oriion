"""CloudEvents emitters for tasks bounded context."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src._shared.cloudevents import emit_cloudevent

_SOURCE = "oriion://contexts/tasks"


async def emit_task_created(
    task_id: UUID,
    cell_id: UUID,
    initiated_by_user_id: UUID,
    parent_task_id: UUID | None = None,
    correlation_id: str | None = None,
) -> None:
    await emit_cloudevent(
        ce_type="oriion.tasks.created.v1",
        source=_SOURCE,
        data={
            "task_id": str(task_id),
            "cell_id": str(cell_id),
            "initiated_by_user_id": str(initiated_by_user_id),
            "parent_task_id": str(parent_task_id) if parent_task_id else None,
        },
        correlation_id=correlation_id,
    )


async def emit_task_started(task_id: UUID, started_at: datetime) -> None:
    await emit_cloudevent(
        ce_type="oriion.tasks.started.v1",
        source=_SOURCE,
        data={"task_id": str(task_id), "started_at": started_at.isoformat()},
    )


async def emit_task_step_completed(
    task_id: UUID,
    step_id: UUID,
    step_type: str,
    cost_credits: Decimal,
    duration_ms: int,
) -> None:
    await emit_cloudevent(
        ce_type="oriion.tasks.step_completed.v1",
        source=_SOURCE,
        data={
            "task_id": str(task_id),
            "step_id": str(step_id),
            "step_type": step_type,
            "cost_credits": str(cost_credits),
            "duration_ms": duration_ms,
        },
    )


async def emit_task_completed(
    task_id: UUID,
    total_cost_credits: Decimal,
    total_duration_ms: int,
    result_summary: dict[str, Any] | None = None,
) -> None:
    await emit_cloudevent(
        ce_type="oriion.tasks.completed.v1",
        source=_SOURCE,
        data={
            "task_id": str(task_id),
            "total_cost_credits": str(total_cost_credits),
            "total_duration_ms": total_duration_ms,
            "result_summary": result_summary or {},
        },
    )


async def emit_task_cancelled(task_id: UUID, cascaded_to: list[UUID]) -> None:
    await emit_cloudevent(
        ce_type="oriion.tasks.cancelled.v1",
        source=_SOURCE,
        data={
            "task_id": str(task_id),
            "cascaded_to_task_ids": [str(t) for t in cascaded_to],
        },
    )


async def emit_task_failed(task_id: UUID, error_code: str, retry_possible: bool) -> None:
    await emit_cloudevent(
        ce_type="oriion.tasks.failed.v1",
        source=_SOURCE,
        data={
            "task_id": str(task_id),
            "error_code": error_code,
            "retry_possible": retry_possible,
        },
    )
