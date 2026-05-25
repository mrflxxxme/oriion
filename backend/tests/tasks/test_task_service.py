"""TaskService — create + get + delegation depth + cancel cascade.

Phase 00.5b runtime invariants asserted via mock session shim.
test_cancel_cascade.py covers the BFS walker thoroughly; this file
covers create + get + depth validation surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from src.tasks.exceptions import DelegationDepthExceeded, TaskNotFound
from src.tasks.models import Task
from src.tasks.services.task_service import TaskService


@dataclass
class _StubResult:
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    scalar: Any = None

    def all(self) -> list[tuple[Any, ...]]:
        return list(self.rows)

    def scalar_one_or_none(self) -> Any:
        return self.scalar


@dataclass
class _StubSession:
    """Mock AsyncSession для TaskService unit tests."""

    get_returns: dict[UUID, Task] = field(default_factory=dict)
    execute_queue: list[_StubResult] = field(default_factory=list)
    added: list[Task] = field(default_factory=list)
    flushed: bool = False

    async def get(self, _model: Any, task_id: UUID) -> Task | None:
        return self.get_returns.get(task_id)

    async def execute(self, _stmt: Any) -> _StubResult:
        if self.execute_queue:
            return self.execute_queue.pop(0)
        return _StubResult()

    def add(self, task: Task) -> None:
        # SQLAlchemy assigns id at flush-time normally; in this stub
        # `add` simulates the post-flush state directly so subsequent
        # session.flush() in TaskService can populate timing fields.
        if getattr(task, "id", None) is None:
            task.id = uuid4()
        if getattr(task, "total_cost_credits", None) is None:
            task.total_cost_credits = Decimal(0)
        self.added.append(task)

    async def flush(self) -> None:
        self.flushed = True


@pytest.fixture
def mock_emit() -> Any:
    with patch("src.tasks.services.task_service.tasks_events") as m:
        m.emit_task_created = AsyncMock()
        m.emit_task_cancelled = AsyncMock()
        yield m


@pytest.mark.asyncio
async def test_create_task_minimal(mock_emit: Any) -> None:
    """Root task creates с no parent + emits task.created event."""
    session = _StubSession()
    svc = TaskService(session)  # type: ignore[arg-type]

    cell_id, user_id = uuid4(), uuid4()
    task = await svc.create_task(
        cell_id=cell_id,
        user_id=user_id,
        title="Test",
        description="desc",
        prompt="hello",
    )
    assert task.cell_id == cell_id
    assert task.initiated_by_user_id == user_id
    assert task.title == "Test"
    assert task.status == "queued"
    assert task.input_jsonb == {"prompt": "hello"}
    assert session.flushed
    assert session.added == [task]
    mock_emit.emit_task_created.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_with_parent_within_depth(mock_emit: Any) -> None:
    """Sub-task with valid parent (depth < 5) succeeds."""
    parent_id = uuid4()
    session = _StubSession(
        # _depth_from_root walks parent chain — return None to terminate at depth 1
        execute_queue=[_StubResult(scalar=None)]
    )
    svc = TaskService(session)  # type: ignore[arg-type]
    task = await svc.create_task(
        cell_id=uuid4(),
        user_id=uuid4(),
        title="Sub",
        description="",
        prompt="p",
        parent_task_id=parent_id,
    )
    assert task.parent_task_id == parent_id
    mock_emit.emit_task_created.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_depth_exceeded() -> None:
    """Sub-task at depth ≥ max_delegation_depth raises DelegationDepthExceeded."""
    parent_id = uuid4()
    # Walk 5 levels: return parent UUIDs ad-infinitum (bounded by safety).
    session = _StubSession(execute_queue=[_StubResult(scalar=uuid4()) for _ in range(10)])
    svc = TaskService(session)  # type: ignore[arg-type]
    with pytest.raises(DelegationDepthExceeded):
        await svc.create_task(
            cell_id=uuid4(),
            user_id=uuid4(),
            title="Too deep",
            description="",
            prompt="p",
            parent_task_id=parent_id,
            max_delegation_depth=3,
        )


@pytest.mark.asyncio
async def test_get_task_found() -> None:
    tid = uuid4()
    task = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="x",
        description="",
        status="queued",
        priority=5,
    )
    task.id = tid
    session = _StubSession(get_returns={tid: task})
    svc = TaskService(session)  # type: ignore[arg-type]
    result = await svc.get_task(tid)
    assert result is task


@pytest.mark.asyncio
async def test_get_task_not_found() -> None:
    session = _StubSession()
    svc = TaskService(session)  # type: ignore[arg-type]
    with pytest.raises(TaskNotFound):
        await svc.get_task(uuid4())


@pytest.mark.asyncio
async def test_cancel_task_no_descendants(mock_emit: Any) -> None:
    """Cancel a leaf task → empty cascade list + 1 update + cancelled event."""
    tid = uuid4()
    task = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="x",
        description="",
        status="running",
        priority=5,
    )
    task.id = tid
    session = _StubSession(
        get_returns={tid: task},
        # BFS first call returns empty → loop terminates; then 1 update.
        execute_queue=[_StubResult(rows=[])],
    )
    svc = TaskService(session)  # type: ignore[arg-type]
    descendants = await svc.cancel_task(tid)
    assert descendants == []
    mock_emit.emit_task_cancelled.assert_awaited_once()
