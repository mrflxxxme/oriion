"""Atomic cost rollup — parent.cost = steps + children.cost.

Stub session plays back a queue of result rows in the order rollup_task_cost
issues queries: every iteration emits [steps_result, children_result] then
calls session.get(Task, current_id) to walk parent chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.tasks.models import Task
from src.tasks.services.cost_rollup_service import rollup_task_cost


@dataclass
class _StubResult:
    rows: list[tuple[Any, ...]] = field(default_factory=list)

    def all(self) -> list[tuple[Any, ...]]:
        return list(self.rows)


@dataclass
class _StubSession:
    """Order-based playback: execute_queue popped LIFO; tasks_by_id served
    к session.get(Task, id). rollup_task_cost issues 2 queries per iteration
    (steps then children) then walks к parent — supply the queue accordingly.
    """

    tasks_by_id: dict[UUID, Task]
    execute_queue: list[_StubResult] = field(default_factory=list)
    flushed: bool = False

    async def get(self, _model: Any, task_id: UUID) -> Task | None:
        return self.tasks_by_id.get(task_id)

    async def execute(self, _stmt: Any) -> _StubResult:
        if not self.execute_queue:
            return _StubResult([])
        return self.execute_queue.pop(0)

    async def flush(self) -> None:
        self.flushed = True


def _make_task(task_id: UUID, parent_id: UUID | None = None) -> Task:
    t = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="t",
        description="",
        status="running",
        priority=5,
    )
    t.id = task_id
    t.parent_task_id = parent_id
    t.total_cost_credits = Decimal(0)
    return t


@pytest.mark.asyncio
async def test_rollup_single_task_no_steps_no_children() -> None:
    """Leaf task с no steps and no children → cost = 0."""
    tid = uuid4()
    task = _make_task(tid)
    session = _StubSession(
        tasks_by_id={tid: task},
        execute_queue=[_StubResult([]), _StubResult([])],  # steps, children
    )
    final = await rollup_task_cost(tid, session)  # type: ignore[arg-type]
    assert final == Decimal(0)
    assert task.total_cost_credits == Decimal(0)
    assert session.flushed


@pytest.mark.asyncio
async def test_rollup_single_task_with_steps() -> None:
    """Leaf task с 3 direct steps → cost = sum(steps)."""
    tid = uuid4()
    task = _make_task(tid)
    session = _StubSession(
        tasks_by_id={tid: task},
        execute_queue=[
            _StubResult([(Decimal("1.5"),), (Decimal("2.5"),), (Decimal("0.25"),)]),  # steps
            _StubResult([]),  # children
        ],
    )
    final = await rollup_task_cost(tid, session)  # type: ignore[arg-type]
    assert final == Decimal("4.25")
    assert task.total_cost_credits == Decimal("4.25")


@pytest.mark.asyncio
async def test_rollup_walks_parent_chain() -> None:
    """Child→parent: parent's cost reflects child's rolled-up cost.

    Order of session.execute() calls:
      Iteration 1 (child):  steps_for_child=[3], children_for_child=[]
      Iteration 2 (parent): steps_for_parent=[1], children_for_parent=[3]
    Then parent.parent_task_id is None → loop exits.
    """
    parent_id, child_id = uuid4(), uuid4()
    parent = _make_task(parent_id)
    child = _make_task(child_id, parent_id=parent_id)
    session = _StubSession(
        tasks_by_id={parent_id: parent, child_id: child},
        execute_queue=[
            _StubResult([(Decimal("3"),)]),  # iter1 steps
            _StubResult([]),  # iter1 children
            _StubResult([(Decimal("1"),)]),  # iter2 steps
            _StubResult([(Decimal("3"),)]),  # iter2 children (child rolled-up)
        ],
    )
    final = await rollup_task_cost(child_id, session)  # type: ignore[arg-type]
    assert final == Decimal("4")  # parent's final cost = 1 + 3
    assert parent.total_cost_credits == Decimal("4")
    assert child.total_cost_credits == Decimal("3")


@pytest.mark.asyncio
async def test_rollup_missing_task_short_circuits() -> None:
    """If session.get returns None mid-walk, loop exits gracefully."""
    missing_id = uuid4()
    session = _StubSession(
        tasks_by_id={},  # nothing
        execute_queue=[_StubResult([]), _StubResult([])],
    )
    final = await rollup_task_cost(missing_id, session)  # type: ignore[arg-type]
    assert final == Decimal(0)


@pytest.mark.asyncio
async def test_rollup_cycle_protection() -> None:
    """visited-set guards against parent_task_id self-loop (data corruption)."""
    tid = uuid4()
    task = _make_task(tid, parent_id=tid)  # self-loop
    session = _StubSession(
        tasks_by_id={tid: task},
        execute_queue=[
            _StubResult([(Decimal("5"),)]),  # steps
            _StubResult([]),  # children
        ],
    )
    final = await rollup_task_cost(tid, session)  # type: ignore[arg-type]
    assert final == Decimal("5")
