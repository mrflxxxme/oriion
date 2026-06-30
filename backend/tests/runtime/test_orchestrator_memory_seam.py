"""Unit: orchestrator ``memory_extraction`` seam (Phase 01.4b C4).

Drives ``execute_agent_task`` with fakes (no PG / no LLM) to assert the seam:
default-None no-op, cost-fold + token-roll on success, best-effort swallow, and
that extraction runs only on the SUCCESS path (grill Q4/Q5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.runtime.orchestrator import OrchestratorContext, execute_agent_task
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.models import Task


class _FakeOutput(BaseModel):
    summary: str = "demo output"


@dataclass
class _FakeRunResult:
    output: _FakeOutput = field(default_factory=_FakeOutput)


class _FakeAgent:
    def __init__(self, *, raise_on_run: BaseException | None = None) -> None:
        self._raise = raise_on_run
        self.run_calls: list[str] = []

    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:
        self.run_calls.append(prompt)
        if self._raise is not None:
            raise self._raise
        return _FakeRunResult()


@dataclass
class _StubSession:
    task: Task | None = None

    async def get(self, _model: Any, _task_id: UUID) -> Task | None:
        return self.task


def _task(task_id: UUID) -> Task:
    t = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="t",
        description="",
        status="queued",
        priority=5,
        input_jsonb={"prompt": "p"},
    )
    t.id = task_id
    t.total_cost_credits = Decimal(0)
    t.total_input_tokens = 0
    t.total_output_tokens = 0
    return t


class _Hook:
    """Records calls; returns a canned (cost, in_tok, out_tok) or raises."""

    def __init__(
        self,
        result: tuple[Decimal, int, int] = (Decimal("0.3"), 12, 8),
        *,
        raise_exc: BaseException | None = None,
    ) -> None:
        self.calls: list[tuple[str, int]] = []
        self._result = result
        self._raise = raise_exc

    async def __call__(self, deliverable: str, step_index: int) -> tuple[Decimal, int, int]:
        self.calls.append((deliverable, step_index))
        if self._raise is not None:
            raise self._raise
        return self._result


async def _noop_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
    raise AssertionError("leaf should not fire")


@pytest.fixture
def _emit() -> Any:
    with patch("src.runtime.orchestrator.tasks_events") as m:
        m.emit_task_started = AsyncMock()
        m.emit_task_completed = AsyncMock()
        m.emit_task_failed = AsyncMock()
        yield m


async def _run(task: Task, publisher: InProcessSSEPublisher, hook: _Hook | None) -> None:
    await execute_agent_task(
        task_id=task.id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=_FakeAgent(),  # type: ignore[arg-type]
        user_prompt="p",
        available_agent_slugs=["researcher"],
        leaf_runner=_noop_leaf,
        sse_publisher=publisher,
        session=_StubSession(task=task),  # type: ignore[arg-type]
        memory_extraction=hook,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_hook_folds_cost_and_rolls_tokens(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    hook = _Hook((Decimal("0.3"), 12, 8))

    await _run(task, publisher, hook)

    assert task.status == "succeeded"
    assert task.total_cost_credits == Decimal("0.3")  # cost folded into the total
    assert task.total_input_tokens == 12  # memory tokens rolled into the totals
    assert task.total_output_tokens == 8
    # hook saw the deliverable (Q7) + the collision-free step_index (0 leaves → 2)
    assert hook.calls == [("demo output", 2)]
    drained = publisher._drain.get(task.id, [])
    step = next(ev for ev in drained if ev.event_type == "task.step_completed")
    assert step.payload["phase"] == "memory_extraction"
    assert step.payload["cost_credits"] == "0.3"


@pytest.mark.asyncio
async def test_default_none_is_noop(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()

    await _run(task, publisher, None)

    assert task.status == "succeeded"
    assert task.total_cost_credits == Decimal(0)
    types = [ev.event_type for ev in publisher._drain.get(task.id, [])]
    assert "task.step_completed" not in types


@pytest.mark.asyncio
async def test_hook_error_is_swallowed_and_task_still_succeeds(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    hook = _Hook(raise_exc=RuntimeError("filter agent melted"))

    await _run(task, publisher, hook)

    assert task.status == "succeeded"  # housekeeping failure never fails the task
    assert task.total_cost_credits == Decimal(0)  # no fold on error
    types = [ev.event_type for ev in publisher._drain.get(task.id, [])]
    assert "task.step_completed" not in types
    assert "task.completed" in types


@pytest.mark.asyncio
async def test_hook_not_called_on_failed_task(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    hook = _Hook()

    with pytest.raises(RuntimeError):
        await execute_agent_task(
            task_id=task.id,
            cell_id=uuid4(),
            user_id=uuid4(),
            coordinator_agent=_FakeAgent(raise_on_run=RuntimeError("boom")),  # type: ignore[arg-type]
            user_prompt="p",
            available_agent_slugs=["researcher"],
            leaf_runner=_noop_leaf,
            sse_publisher=publisher,
            session=_StubSession(task=task),  # type: ignore[arg-type]
            memory_extraction=hook,  # type: ignore[arg-type]
        )

    assert task.status == "failed"
    assert hook.calls == []  # extraction runs only on the success path (Q4)
