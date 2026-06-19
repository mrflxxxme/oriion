"""AC12 anchor: cancel task cascades to ALL descendants atomically.

Phase 00.5b Commit 7. TaskService.cancel_task() walks the parent_task_id
DAG via BFS and flips every descendant to status='cancelled' in one
UPDATE statement (atomic per PostgreSQL TX semantics).

This unit test exercises the BFS walker + cancel-event emission via an
in-memory session shim. Real testcontainers PG validation lives in the
Wave-1 testcontainers migration (SLIP-candidate F-P5-3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest


@dataclass
class _StubResult:
    """sqlalchemy.Result-shaped stub. `.all()` returns the prepared rows
    synchronously; `.scalar_one_or_none()` returns the prepared scalar."""

    rows: list[tuple[Any, ...]] = field(default_factory=list)
    scalar: Any = None

    def all(self) -> list[tuple[Any, ...]]:
        return list(self.rows)

    def scalar_one_or_none(self) -> Any:
        return self.scalar


@dataclass
class _StubSession:
    """Just-enough AsyncSession shim for TaskService.cancel_task.

    Plays back a queue of _StubResult instances on successive .execute()
    calls. Real session.get() returns the supplied root_task object.
    """

    root_task: Any
    execute_queue: list[_StubResult]
    added: list[Any] = field(default_factory=list)

    async def get(self, _model: Any, _id: UUID) -> Any:
        return self.root_task

    async def execute(self, _stmt: Any) -> _StubResult:
        # Pop in order. cancel_task issues:
        #   1. BFS depth-1: select children of root.
        #   2. BFS depth-2..N: select children of frontier.
        #   3. Final UPDATE: results never inspected (we still pop a stub).
        if not self.execute_queue:
            return _StubResult()
        return self.execute_queue.pop(0)

    # AC-W1-4: cancel_task now also writes a task.cancelled outbox row in the
    # same TX (TaskRepository.add_outbox_event) — track adds so a test can assert
    # whether a cancelled event was (not) emitted.
    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_cancel_task_cascade_collects_descendants() -> None:
    """BFS walker returns the full set of descendant task IDs."""
    from src.tasks.models import Task
    from src.tasks.services.task_service import TaskService

    root_id = uuid4()
    a, b, c = uuid4(), uuid4(), uuid4()

    fake_root = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="root",
        description="",
        status="running",
        priority=5,
    )
    fake_root.id = root_id

    session = _StubSession(
        root_task=fake_root,
        execute_queue=[
            _StubResult(rows=[(a,), (b,)]),  # depth 1: a, b
            _StubResult(rows=[(c,)]),  # depth 2: c (child of a or b)
            _StubResult(rows=[]),  # depth 3: empty, exit BFS
            _StubResult(),  # the atomic UPDATE
        ],
    )

    service = TaskService(session)  # type: ignore[arg-type]
    descendants = await service.cancel_task(root_id)

    assert set(descendants) == {a, b, c}
    assert len(descendants) == 3


@pytest.mark.asyncio
async def test_cancel_task_with_no_descendants_returns_empty() -> None:
    """Cancelling a leaf task returns an empty descendant list (still
    flips the task itself)."""
    from src.tasks.models import Task
    from src.tasks.services.task_service import TaskService

    root_id = uuid4()
    fake_root = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="leaf",
        description="",
        status="running",
        priority=5,
    )
    fake_root.id = root_id

    session = _StubSession(
        root_task=fake_root,
        execute_queue=[
            _StubResult(rows=[]),  # depth 1: no children
            _StubResult(),  # UPDATE
        ],
    )

    service = TaskService(session)  # type: ignore[arg-type]
    descendants = await service.cancel_task(root_id)
    assert descendants == []


@pytest.mark.asyncio
async def test_cancel_task_already_terminal_is_noop() -> None:
    """A root already in a terminal state is not re-cancelled: returns [] and
    writes NO duplicate tasks.cancelled outbox event (idempotent re-cancel)."""
    from src.tasks.models import Task
    from src.tasks.services.task_service import TaskService

    root_id = uuid4()
    fake_root = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="done",
        description="",
        status="cancelled",  # terminal
        priority=5,
    )
    fake_root.id = root_id

    session = _StubSession(root_task=fake_root, execute_queue=[])
    service = TaskService(session)  # type: ignore[arg-type]

    descendants = await service.cancel_task(root_id)

    assert descendants == []
    assert session.added == []  # no outbox event emitted — no real transition


@pytest.mark.asyncio
async def test_descendant_ids_terminates_on_cycle() -> None:
    """A parent_task_id cycle must not loop forever — the visited-set guard stops
    once a frontier child points back at an already-seen node."""
    from src.tasks.services.repository import SqlAlchemyTaskRepository

    root_id = uuid4()
    b = uuid4()
    # root -> b -> root (cycle). The second hop returns root, already visited.
    session = _StubSession(
        root_task=None,
        execute_queue=[
            _StubResult(rows=[(b,)]),  # children of root = b
            _StubResult(rows=[(root_id,)]),  # children of b = root (visited) -> stop
        ],
    )
    repo = SqlAlchemyTaskRepository(session)  # type: ignore[arg-type]

    result = await repo.descendant_ids(root_id)

    assert result == [b]  # terminates; root not re-traversed


@pytest.mark.asyncio
async def test_cancel_task_not_found_raises() -> None:
    """get_task raises TaskNotFound when the row doesn't exist."""
    from src.tasks.exceptions import TaskNotFound
    from src.tasks.services.task_service import TaskService

    session = _StubSession(root_task=None, execute_queue=[])

    service = TaskService(session)  # type: ignore[arg-type]
    with pytest.raises(TaskNotFound):
        await service.cancel_task(uuid4())
