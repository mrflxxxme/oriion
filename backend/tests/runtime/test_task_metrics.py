"""AC-W1-13: the orchestrator emits task_duration_seconds / task_total /
task_queue_depth on terminal transitions.

Each test uses a fresh random cell_id so the per-cell labels are unique and can
be asserted absolutely; the shared role_key histogram is checked by delta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from prometheus_client import REGISTRY
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

    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:  # noqa: ARG002
        if self._raise is not None:
            raise self._raise
        return _FakeRunResult()


@dataclass
class _StubSession:
    task: Task | None = None

    async def get(self, _model: Any, _task_id: UUID) -> Task | None:
        return self.task


def _build_task(task_id: UUID, cell_id: UUID) -> Task:
    t = Task(
        cell_id=cell_id,
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


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


async def _noop_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
    raise AssertionError("leaf_runner must not fire on the no-delegation path")


@pytest.mark.asyncio
async def test_succeeded_task_emits_duration_total_and_releases_gauge() -> None:
    cell_id = uuid4()
    cell_label = str(cell_id)
    task_id = uuid4()
    session = _StubSession(task=_build_task(task_id, cell_id))

    before_dur = _sample(
        "task_duration_seconds_count", {"role_key": "coordinator", "outcome": "succeeded"}
    )

    await execute_agent_task(
        task_id=task_id,
        cell_id=cell_id,
        user_id=uuid4(),
        coordinator_agent=_FakeAgent(),  # type: ignore[arg-type]
        user_prompt="x",
        available_agent_slugs=["researcher"],
        leaf_runner=_noop_leaf,
        sse_publisher=InProcessSSEPublisher(),
        session=session,  # type: ignore[arg-type]
    )

    assert _sample("task_total", {"cell_id": cell_label, "outcome": "succeeded"}) == 1
    # inc at start, dec at terminal → nets to 0 for this fresh cell.
    assert _sample("task_queue_depth", {"cell_id": cell_label}) == 0
    assert (
        _sample("task_duration_seconds_count", {"role_key": "coordinator", "outcome": "succeeded"})
        == before_dur + 1
    )


@pytest.mark.asyncio
async def test_failed_task_emits_failed_outcome_and_releases_gauge() -> None:
    cell_id = uuid4()
    cell_label = str(cell_id)
    task_id = uuid4()
    session = _StubSession(task=_build_task(task_id, cell_id))

    with pytest.raises(ValueError):
        await execute_agent_task(
            task_id=task_id,
            cell_id=cell_id,
            user_id=uuid4(),
            coordinator_agent=_FakeAgent(raise_on_run=ValueError("boom")),  # type: ignore[arg-type]
            user_prompt="x",
            available_agent_slugs=["researcher"],
            leaf_runner=_noop_leaf,
            sse_publisher=InProcessSSEPublisher(),
            session=session,  # type: ignore[arg-type]
        )

    assert _sample("task_total", {"cell_id": cell_label, "outcome": "failed"}) == 1
    assert _sample("task_queue_depth", {"cell_id": cell_label}) == 0


@pytest.mark.asyncio
async def test_budget_exceeded_maps_to_dedicated_outcome() -> None:
    cell_id = uuid4()
    cell_label = str(cell_id)
    task_id = uuid4()
    session = _StubSession(task=_build_task(task_id, cell_id))

    class _BudgetError(RuntimeError):
        code = "llm_gateway.budget_exceeded"

    with pytest.raises(_BudgetError):
        await execute_agent_task(
            task_id=task_id,
            cell_id=cell_id,
            user_id=uuid4(),
            coordinator_agent=_FakeAgent(raise_on_run=_BudgetError("over")),  # type: ignore[arg-type]
            user_prompt="x",
            available_agent_slugs=["researcher"],
            leaf_runner=_noop_leaf,
            sse_publisher=InProcessSSEPublisher(),
            session=session,  # type: ignore[arg-type]
        )

    assert _sample("task_total", {"cell_id": cell_label, "outcome": "budget_exceeded"}) == 1
    assert _sample("task_total", {"cell_id": cell_label, "outcome": "failed"}) == 0
