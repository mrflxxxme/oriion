"""Unit: TaskRepository outbox writes + TaskService routing through it (AC-W1-4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.tasks.exceptions import DelegationDepthExceeded
from src.tasks.models import OutboxEvent, Task
from src.tasks.services.repository import SqlAlchemyTaskRepository, TaskRepository
from src.tasks.services.task_service import TaskService


@dataclass
class _Res:
    scalar_list: list[Any] = field(default_factory=list)
    scalar: Any = None
    rows: list[Any] = field(default_factory=list)

    def scalars(self) -> Any:
        return _Scalars(self.scalar_list)

    def scalar_one_or_none(self) -> Any:
        return self.scalar

    def all(self) -> list[Any]:
        return list(self.rows)


@dataclass
class _Scalars:
    items: list[Any]

    def all(self) -> list[Any]:
        return list(self.items)


class _StubSession:
    def __init__(self, *, get_result: Any = None, execute: list[_Res] | None = None) -> None:
        self.added: list[Any] = []
        self.flushes = 0
        self._get = get_result
        self._execute = list(execute or [])

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1

    async def get(self, _model: Any, _id: UUID) -> Any:
        return self._get

    async def execute(self, _stmt: Any) -> _Res:
        return self._execute.pop(0) if self._execute else _Res()


@pytest.mark.asyncio
async def test_repository_add_outbox_event_inserts_row() -> None:
    session = _StubSession()
    repo = SqlAlchemyTaskRepository(session)  # type: ignore[arg-type]

    event = await repo.add_outbox_event(
        ce_type="oriion.tasks.created.v1",
        ce_source="oriion://contexts/tasks",
        data={"task_id": "x"},
    )

    assert isinstance(event, OutboxEvent)
    assert event in session.added
    assert session.flushes == 1
    assert event.ce_type == "oriion.tasks.created.v1"


@pytest.mark.asyncio
async def test_repository_descendant_ids_bfs() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    session = _StubSession(execute=[_Res(rows=[(a,), (b,)]), _Res(rows=[(c,)]), _Res(rows=[])])
    repo = SqlAlchemyTaskRepository(session)  # type: ignore[arg-type]

    assert set(await repo.descendant_ids(uuid4())) == {a, b, c}


# ── TaskService routes state-change events through the outbox ───────────────


class _FakeRepo:
    """In-memory TaskRepository capturing outbox writes + cascade calls."""

    def __init__(
        self, *, get_result: Task | None = None, descendants: list[UUID] | None = None
    ) -> None:
        self.added: list[Task] = []
        self.outbox: list[dict[str, Any]] = []
        self.cancelled_ids: list[UUID] | None = None
        self._get = get_result
        self._descendants = descendants or []
        self.parent_chain: dict[UUID, UUID | None] = {}

    async def add(self, task: Task) -> Task:
        if getattr(task, "id", None) is None:
            task.id = uuid4()
        self.added.append(task)
        return task

    async def get(self, task_id: UUID) -> Task | None:
        return self._get

    async def parent_id(self, task_id: UUID) -> UUID | None:
        return self.parent_chain.get(task_id)

    async def descendant_ids(self, root_id: UUID) -> list[UUID]:
        return list(self._descendants)

    async def cancel_cascade(self, task_ids: list[UUID], *, at: datetime) -> None:
        self.cancelled_ids = list(task_ids)

    async def add_outbox_event(
        self,
        *,
        ce_type: str,
        ce_source: str,
        data: dict[str, Any],
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> OutboxEvent:
        self.outbox.append({"ce_type": ce_type, "data": data})
        return OutboxEvent(ce_type=ce_type, ce_source=ce_source, data=data)


def _repo_as_port(repo: _FakeRepo) -> TaskRepository:
    return repo  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_create_task_writes_created_outbox_event() -> None:
    repo = _FakeRepo()
    service = TaskService(session=None, repository=_repo_as_port(repo))  # type: ignore[arg-type]

    task = await service.create_task(
        cell_id=uuid4(), user_id=uuid4(), title="t", description="d", prompt="p"
    )

    assert len(repo.outbox) == 1
    assert repo.outbox[0]["ce_type"] == "oriion.tasks.created.v1"
    assert repo.outbox[0]["data"]["task_id"] == str(task.id)


@pytest.mark.asyncio
async def test_cancel_task_writes_cancelled_outbox_event() -> None:
    root_id = uuid4()
    root = Task(cell_id=uuid4(), initiated_by_user_id=uuid4(), title="r", description="")
    root.id = root_id
    child = uuid4()
    repo = _FakeRepo(get_result=root, descendants=[child])
    service = TaskService(session=None, repository=_repo_as_port(repo))  # type: ignore[arg-type]

    out = await service.cancel_task(root_id)

    assert out == [child]
    assert repo.cancelled_ids == [root_id, child]
    assert repo.outbox[-1]["ce_type"] == "oriion.tasks.cancelled.v1"
    assert repo.outbox[-1]["data"]["cascaded_to_task_ids"] == [str(child)]


@pytest.mark.asyncio
async def test_create_task_enforces_depth_limit() -> None:
    parent = uuid4()
    repo = _FakeRepo()
    # parent → grandparent → ... a chain longer than the cap.
    chain: UUID | None = parent
    for _ in range(6):
        nxt = uuid4()
        repo.parent_chain[chain] = nxt  # type: ignore[index]
        chain = nxt
    service = TaskService(session=None, repository=_repo_as_port(repo))  # type: ignore[arg-type]

    with pytest.raises(DelegationDepthExceeded):
        await service.create_task(
            cell_id=uuid4(),
            user_id=uuid4(),
            title="t",
            description="d",
            prompt="p",
            parent_task_id=parent,
            max_delegation_depth=3,
        )
