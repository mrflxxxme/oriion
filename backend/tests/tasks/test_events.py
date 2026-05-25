"""CloudEvents emitters — shape + correlation id propagation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.tasks import events as tasks_events


@pytest.fixture
def mock_emit() -> Any:
    """Patch _shared.cloudevents.emit_cloudevent so tests assert call shape
    без I/O. Returns the AsyncMock instance for inspection."""
    with patch("src.tasks.events.emit_cloudevent", new_callable=AsyncMock) as m:
        yield m


@pytest.mark.asyncio
async def test_emit_task_created_minimal(mock_emit: AsyncMock) -> None:
    task_id, cell_id, user_id = uuid4(), uuid4(), uuid4()
    await tasks_events.emit_task_created(
        task_id=task_id, cell_id=cell_id, initiated_by_user_id=user_id
    )
    mock_emit.assert_awaited_once()
    args = mock_emit.call_args
    assert args.kwargs["ce_type"] == "oriion.tasks.created.v1"
    assert args.kwargs["source"] == "oriion://contexts/tasks"
    assert args.kwargs["data"]["task_id"] == str(task_id)
    assert args.kwargs["data"]["parent_task_id"] is None
    assert args.kwargs["correlation_id"] is None


@pytest.mark.asyncio
async def test_emit_task_created_with_parent_and_corr(mock_emit: AsyncMock) -> None:
    parent = uuid4()
    await tasks_events.emit_task_created(
        task_id=uuid4(),
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        parent_task_id=parent,
        correlation_id="corr-123",
    )
    args = mock_emit.call_args
    assert args.kwargs["data"]["parent_task_id"] == str(parent)
    assert args.kwargs["correlation_id"] == "corr-123"


@pytest.mark.asyncio
async def test_emit_task_started(mock_emit: AsyncMock) -> None:
    task_id = uuid4()
    started = datetime.now(UTC)
    await tasks_events.emit_task_started(task_id=task_id, started_at=started)
    args = mock_emit.call_args
    assert args.kwargs["ce_type"] == "oriion.tasks.started.v1"
    assert args.kwargs["data"]["started_at"] == started.isoformat()


@pytest.mark.asyncio
async def test_emit_task_step_completed(mock_emit: AsyncMock) -> None:
    await tasks_events.emit_task_step_completed(
        task_id=uuid4(),
        step_id=uuid4(),
        step_type="researcher",
        cost_credits=Decimal("2.50"),
        duration_ms=1234,
    )
    args = mock_emit.call_args
    assert args.kwargs["ce_type"] == "oriion.tasks.step_completed.v1"
    assert args.kwargs["data"]["step_type"] == "researcher"
    assert args.kwargs["data"]["cost_credits"] == "2.50"
    assert args.kwargs["data"]["duration_ms"] == 1234


@pytest.mark.asyncio
async def test_emit_task_completed_default_summary(mock_emit: AsyncMock) -> None:
    await tasks_events.emit_task_completed(
        task_id=uuid4(), total_cost_credits=Decimal("10"), total_duration_ms=5000
    )
    args = mock_emit.call_args
    assert args.kwargs["ce_type"] == "oriion.tasks.completed.v1"
    assert args.kwargs["data"]["result_summary"] == {}


@pytest.mark.asyncio
async def test_emit_task_completed_with_summary(mock_emit: AsyncMock) -> None:
    await tasks_events.emit_task_completed(
        task_id=uuid4(),
        total_cost_credits=Decimal("13.5"),
        total_duration_ms=98000,
        result_summary={"brief_words": 1554, "matrix_rows": 5},
    )
    args = mock_emit.call_args
    assert args.kwargs["data"]["result_summary"] == {"brief_words": 1554, "matrix_rows": 5}


@pytest.mark.asyncio
async def test_emit_task_cancelled(mock_emit: AsyncMock) -> None:
    root, child_a, child_b = uuid4(), uuid4(), uuid4()
    await tasks_events.emit_task_cancelled(task_id=root, cascaded_to=[child_a, child_b])
    args = mock_emit.call_args
    assert args.kwargs["ce_type"] == "oriion.tasks.cancelled.v1"
    assert args.kwargs["data"]["cascaded_to_task_ids"] == [str(child_a), str(child_b)]


@pytest.mark.asyncio
async def test_emit_task_failed(mock_emit: AsyncMock) -> None:
    await tasks_events.emit_task_failed(
        task_id=uuid4(), error_code="llm_gateway.budget_exceeded", retry_possible=False
    )
    args = mock_emit.call_args
    assert args.kwargs["ce_type"] == "oriion.tasks.failed.v1"
    assert args.kwargs["data"]["error_code"] == "llm_gateway.budget_exceeded"
    assert args.kwargs["data"]["retry_possible"] is False
