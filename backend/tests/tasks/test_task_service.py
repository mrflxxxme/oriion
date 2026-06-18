"""TaskService — create + get + delegation depth + cancel cascade.

Phase 00.5b runtime invariants asserted via mock session shim.
test_cancel_cascade.py covers the BFS walker thoroughly; this file
covers create + get + depth validation surfaces. AC-W1-4: state-change events
are now written to the transactional outbox (via TaskRepository.add_outbox_event)
in the same TX, so they surface as OutboxEvent rows in ``session.added``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.tasks.exceptions import DelegationDepthExceeded, TaskNotFound
from src.tasks.models import OutboxEvent, Task
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
    added: list[Any] = field(default_factory=list)
    flushed: bool = False

    async def get(self, _model: Any, task_id: UUID) -> Task | None:
        return self.get_returns.get(task_id)

    async def execute(self, _stmt: Any) -> _StubResult:
        if self.execute_queue:
            return self.execute_queue.pop(0)
        return _StubResult()

    def add(self, obj: Any) -> None:
        # SQLAlchemy assigns id at flush-time normally; the stub simulates the
        # post-flush state directly so id is populated for both Task + OutboxEvent.
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if isinstance(obj, Task) and getattr(obj, "total_cost_credits", None) is None:
            obj.total_cost_credits = Decimal(0)
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed = True


def _outbox_rows(session: _StubSession) -> list[OutboxEvent]:
    return [o for o in session.added if isinstance(o, OutboxEvent)]


@pytest.mark.asyncio
async def test_create_task_minimal() -> None:
    """Root task creates with no parent + writes a task.created outbox event."""
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
    assert task.status == "queued"
    assert task.input_jsonb == {"prompt": "hello"}
    assert session.flushed
    assert task in session.added
    events = _outbox_rows(session)
    assert len(events) == 1
    assert events[0].ce_type == "oriion.tasks.created.v1"
    assert events[0].data["task_id"] == str(task.id)


@pytest.mark.asyncio
async def test_create_task_with_parent_within_depth() -> None:
    """Sub-task with valid parent (depth < 5) succeeds + emits to outbox."""
    parent_id = uuid4()
    session = _StubSession(
        # _depth_from_root walks parent chain — None terminates at depth 1.
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
    assert _outbox_rows(session)[0].ce_type == "oriion.tasks.created.v1"


@pytest.mark.asyncio
async def test_create_task_depth_exceeded() -> None:
    """Sub-task at depth ≥ max_delegation_depth raises DelegationDepthExceeded."""
    parent_id = uuid4()
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
async def test_cancel_task_no_descendants() -> None:
    """Cancel a leaf task → empty cascade + 1 update + cancelled outbox event."""
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
        execute_queue=[_StubResult(rows=[])],  # BFS empty → terminates
    )
    svc = TaskService(session)  # type: ignore[arg-type]
    descendants = await svc.cancel_task(tid)
    assert descendants == []
    events = _outbox_rows(session)
    assert len(events) == 1
    assert events[0].ce_type == "oriion.tasks.cancelled.v1"
