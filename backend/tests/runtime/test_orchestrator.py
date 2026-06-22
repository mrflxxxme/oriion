"""Orchestrator state machine — happy path + task.failed exception branch.

Uses fake Coordinator Agent + fake leaf_runner + in-process SSE publisher
so no Pydantic-AI provider chain needs to be reachable. Covers the
F-ARC-M2 audit fix path (try/except wrapping Agent.run() emits task.failed +
refunds budget on exception).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.billing.exceptions import CellQuotaExceeded
from src.billing.services.quota_service import QuotaStatus
from src.runtime.orchestrator import (
    OrchestratorContext,
    estimate_step_cost,
    execute_agent_task,
)
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.exceptions import BudgetExceeded
from src.tasks.models import Task

# ── Test doubles ────────────────────────────────────────────────────────


class _FakeOutput(BaseModel):
    summary: str = "demo output"


@dataclass
class _FakeRunResult:
    output: _FakeOutput = field(default_factory=_FakeOutput)


class _FakeAgent:
    """Stand-in for pydantic_ai.Agent. ``run()`` returns canned output OR
    raises (if `raise_on_run` is set)."""

    def __init__(self, *, raise_on_run: BaseException | None = None) -> None:
        self._raise = raise_on_run
        self.run_calls: list[Any] = []

    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:
        self.run_calls.append({"prompt": prompt, "deps": deps})
        if self._raise is not None:
            raise self._raise
        return _FakeRunResult()


@dataclass
class _StubSession:
    """Session shim — session.get(Task, id) returns the supplied task row."""

    task: Task | None = None

    async def get(self, _model: Any, _task_id: UUID) -> Task | None:
        return self.task


def _build_fake_task(task_id: UUID) -> Task:
    t = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="Test task",
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


@pytest.fixture
def mock_emit() -> Any:
    """Patch tasks_events emit_* so we can assert на call shape."""
    with patch("src.runtime.orchestrator.tasks_events") as m:
        m.emit_task_started = AsyncMock()
        m.emit_task_completed = AsyncMock()
        m.emit_task_failed = AsyncMock()
        yield m


# ── Happy path ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_happy_path_emits_full_sse_ledger(mock_emit: Any) -> None:
    """Coordinator returns без delegations → started + completed events.

    Covers task.status flip queued→running→succeeded, cost rollup, output
    serialization via model_dump.
    """
    task_id = uuid4()
    cell_id = uuid4()
    user_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()

    async def _noop_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        # Not called в this scenario (Coordinator returns directly).
        raise AssertionError("leaf_runner should not fire on no-delegation path")

    agent = _FakeAgent()
    result = await execute_agent_task(
        task_id=task_id,
        cell_id=cell_id,
        user_id=user_id,
        coordinator_agent=agent,  # type: ignore[arg-type]
        user_prompt="Test prompt",
        available_agent_slugs=["researcher", "writer", "analyst"],
        leaf_runner=_noop_leaf,
        sse_publisher=publisher,
        session=session,  # type: ignore[arg-type]
    )

    # Output shape: model_dump of FakeOutput + injected total_cost_credits.
    assert result["summary"] == "demo output"
    assert result["total_cost_credits"] == "0"

    # Task state flipped к succeeded.
    assert task.status == "succeeded"
    assert task.completed_at is not None
    assert task.started_at is not None
    assert task.total_cost_credits == Decimal(0)
    assert task.total_output_tokens == 0  # no leaf delegations = 0 tokens

    # SSE event ledger — drain buffer holds all published events.
    drained = publisher._drain.get(task_id, [])
    types = [ev.event_type for ev in drained]
    assert types == ["task.started", "task.completed"]
    assert task_id in publisher._completed

    # CloudEvents fired.
    mock_emit.emit_task_started.assert_awaited_once()
    mock_emit.emit_task_completed.assert_awaited_once()
    mock_emit.emit_task_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_happy_path_with_delegation(mock_emit: Any) -> None:
    """Coordinator delegates 2x → orchestrator emits delegation_started +
    delegation_completed per call + sums cost into accumulated_cost.

    Uses a FakeAgent that invokes the runner_with_orchestration callable
    в deps как Coordinator's `delegate_task` tool would in production.
    """
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()

    leaf_calls: list[DelegateInput] = []

    async def _leaf_runner(inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        leaf_calls.append(inp)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output="leaf done",
            cost_credits=Decimal("2.5"),
            tokens_used=120,
        )

    class _FakeAgentDispatching:
        run_calls: ClassVar[list[Any]] = []

        async def run(self, _prompt: str, *, deps: Any) -> _FakeRunResult:
            # Simulate Coordinator invoking delegate_task twice through deps.runner.
            await deps.runner(
                DelegateInput(target_agent_slug="researcher", sub_prompt="r-prompt"),
                deps,
            )
            await deps.runner(
                DelegateInput(target_agent_slug="writer", sub_prompt="w-prompt"),
                deps,
            )
            return _FakeRunResult()

    await execute_agent_task(
        task_id=task_id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=_FakeAgentDispatching(),  # type: ignore[arg-type]
        user_prompt="prompt",
        available_agent_slugs=["researcher", "writer"],
        leaf_runner=_leaf_runner,
        sse_publisher=publisher,
        session=session,  # type: ignore[arg-type]
    )

    assert len(leaf_calls) == 2
    drained = publisher._drain.get(task_id, [])
    types = [ev.event_type for ev in drained]
    assert types == [
        "task.started",
        "task.delegation_started",
        "task.delegation_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.completed",
    ]
    # Cost accumulated: 2.5 + 2.5 = 5.0
    assert task.total_cost_credits == Decimal("5.0")
    # Tokens summed: 120 + 120 = 240
    assert task.total_output_tokens == 240


# ── Failed path ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_run_exception_emits_task_failed_and_reraises(
    mock_emit: Any,
) -> None:
    """F-ARC-M2 fix: Agent.run() raising → task.failed SSE + emit_task_failed
    + budget refund + status='failed' + re-raise to caller."""
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()

    class _BoomError(RuntimeError):
        code = "llm_gateway.budget_exceeded"

    agent = _FakeAgent(raise_on_run=_BoomError("provider melted"))

    async def _unused_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        raise AssertionError("leaf should not fire — Agent.run raises first")

    with pytest.raises(_BoomError):
        await execute_agent_task(
            task_id=task_id,
            cell_id=uuid4(),
            user_id=uuid4(),
            coordinator_agent=agent,  # type: ignore[arg-type]
            user_prompt="will explode",
            available_agent_slugs=["researcher"],
            leaf_runner=_unused_leaf,
            sse_publisher=publisher,
            session=session,  # type: ignore[arg-type]
        )

    # Task state — failed, completed_at stamped, cost=0.
    assert task.status == "failed"
    assert task.completed_at is not None
    assert task.total_cost_credits == Decimal(0)

    # SSE ledger — task.started followed by task.failed (no task.completed).
    drained = publisher._drain.get(task_id, [])
    types = [ev.event_type for ev in drained]
    assert types == ["task.started", "task.failed"]
    # The .failed event carries the error code per F-ARC-M2 contract.
    failed_event = next(ev for ev in drained if ev.event_type == "task.failed")
    assert failed_event.payload["error_code"] == "llm_gateway.budget_exceeded"
    assert failed_event.payload["retry_possible"] is False

    # CloudEvents fired: started + failed; NOT completed.
    mock_emit.emit_task_started.assert_awaited_once()
    mock_emit.emit_task_failed.assert_awaited_once()
    mock_emit.emit_task_completed.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_run_exception_without_code_uses_classname(mock_emit: Any) -> None:
    """Exception без `.code` attribute → orchestrator falls back to class name."""
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()

    agent = _FakeAgent(raise_on_run=ValueError("plain value error"))

    async def _unused(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        raise AssertionError

    with pytest.raises(ValueError):
        await execute_agent_task(
            task_id=task_id,
            cell_id=uuid4(),
            user_id=uuid4(),
            coordinator_agent=agent,  # type: ignore[arg-type]
            user_prompt="x",
            available_agent_slugs=["w"],
            leaf_runner=_unused,
            sse_publisher=publisher,
            session=session,  # type: ignore[arg-type]
        )

    drained = publisher._drain.get(task_id, [])
    failed_event = next(ev for ev in drained if ev.event_type == "task.failed")
    assert failed_event.payload["error_code"] == "ValueError"


# ── Edge: missing task ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_missing_in_session_still_completes(mock_emit: Any) -> None:
    """session.get returns None (task purged race) — orchestrator still
    publishes SSE ledger but skips task-row updates."""
    task_id = uuid4()
    session = _StubSession(task=None)  # No task row!
    publisher = InProcessSSEPublisher()

    async def _noop(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        raise AssertionError

    agent = _FakeAgent()
    result = await execute_agent_task(
        task_id=task_id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=agent,  # type: ignore[arg-type]
        user_prompt="x",
        available_agent_slugs=["w"],
        leaf_runner=_noop,
        sse_publisher=publisher,
        session=session,  # type: ignore[arg-type]
    )
    assert result["summary"] == "demo output"
    drained = publisher._drain.get(task_id, [])
    assert [ev.event_type for ev in drained] == ["task.started", "task.completed"]


# ── P1-D: per-step pre-call budget enforcement ────────────────────────────


@pytest.mark.asyncio
async def test_step_rejected_before_call_when_projected_cost_exceeds_cap(
    mock_emit: Any,
) -> None:
    """P1-D fix: a step whose forward cost estimate would blow the per-task cap
    is rejected (BudgetExceeded) BEFORE the paid leaf call — the leaf_runner
    never fires. Previously check_budget ran with pending_cost=0 so the
    expensive step always ran in full and only tripped the AFTER-check.

    The writer's forward estimate is max_tokens(8192) * 0.000110 ≈ 0.901
    credits; a 0.5-credit cap must reject it up-front.
    """
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()

    # Sanity: writer's projected step cost exceeds the tiny cap below.
    assert estimate_step_cost("writer") > Decimal("0.5")

    leaf_fired = False

    async def _leaf_runner(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        nonlocal leaf_fired
        leaf_fired = True
        raise AssertionError("leaf_runner must NOT fire — step is over-budget pre-call")

    class _DelegatingAgent:
        async def run(self, _prompt: str, *, deps: Any) -> _FakeRunResult:
            await deps.runner(
                DelegateInput(target_agent_slug="writer", sub_prompt="w"),
                deps,
            )
            return _FakeRunResult()

    with pytest.raises(BudgetExceeded):
        await execute_agent_task(
            task_id=task_id,
            cell_id=uuid4(),
            user_id=uuid4(),
            coordinator_agent=_DelegatingAgent(),  # type: ignore[arg-type]
            user_prompt="p",
            available_agent_slugs=["writer"],
            leaf_runner=_leaf_runner,
            sse_publisher=publisher,
            session=session,  # type: ignore[arg-type]
            budget_cap=Decimal("0.5"),
        )

    assert leaf_fired is False  # rejected BEFORE the paid call
    assert task.status == "failed"  # budget breach is a terminal failure
    drained = publisher._drain.get(task_id, [])
    failed = next(ev for ev in drained if ev.event_type == "task.failed")
    assert failed.payload["error_code"] == "tasks.budget_exceeded"


# ── P1-C: mid-run cancel stops orchestration, no success-write resurrection ──


class _CancelOnRefreshSession:
    """Session shim that flips the row to 'cancelled' on the first refresh —
    models a concurrent cancel_task commit landing mid-run."""

    def __init__(self, task: Task) -> None:
        self.task = task
        self.refreshes = 0

    async def get(self, _model: Any, _task_id: UUID) -> Task | None:
        return self.task

    async def refresh(self, obj: Any, attribute_names: Any = None) -> None:
        self.refreshes += 1
        obj.status = "cancelled"  # cancel landed (committed on another session)


@pytest.mark.asyncio
async def test_cancel_mid_run_ends_cancelled_and_stops_further_steps(
    mock_emit: Any,
) -> None:
    """P1-C fix: a task cancelled mid-run ends terminal 'cancelled' (NOT
    'succeeded') and issues no further delegation steps after the cancel.

    The Coordinator tries to delegate twice; the first runner call re-reads the
    persisted status (now 'cancelled') and raises TaskCancelled, so the second
    step never runs and the success-write never resurrects the row.
    """
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _CancelOnRefreshSession(task)
    publisher = InProcessSSEPublisher()

    leaf_calls: list[DelegateInput] = []

    async def _leaf_runner(inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        leaf_calls.append(inp)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output="x",
            cost_credits=Decimal("1"),
            tokens_used=10,
        )

    class _TwoStepAgent:
        async def run(self, _prompt: str, *, deps: Any) -> _FakeRunResult:
            await deps.runner(DelegateInput(target_agent_slug="researcher", sub_prompt="r"), deps)
            await deps.runner(DelegateInput(target_agent_slug="writer", sub_prompt="w"), deps)
            return _FakeRunResult()

    mock_emit.emit_task_cancelled = AsyncMock()
    result = await execute_agent_task(
        task_id=task_id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=_TwoStepAgent(),  # type: ignore[arg-type]
        user_prompt="p",
        available_agent_slugs=["researcher", "writer"],
        leaf_runner=_leaf_runner,
        sse_publisher=publisher,
        session=session,  # type: ignore[arg-type]
    )

    # Terminal 'cancelled', NOT resurrected to 'succeeded'.
    assert task.status == "cancelled"
    assert result["summary"] == "(cancelled)"
    # No delegation step ran (cancel detected before the first leaf call).
    assert leaf_calls == []
    # SSE ledger ends on task.cancelled, never task.completed.
    types = [ev.event_type for ev in publisher._drain.get(task_id, [])]
    assert "task.cancelled" in types
    assert "task.completed" not in types
    mock_emit.emit_task_cancelled.assert_awaited_once()


# ── AC-01.3.5/.6: quota_admission seam wiring ─────────────────────────────


@pytest.mark.asyncio
async def test_quota_admission_hard_block_fails_task(mock_emit: Any) -> None:
    """A quota_admission that raises CellQuotaExceeded fails the task BEFORE the
    Coordinator runs, emitting task.failed with the billing code (AC-01.3.5)."""
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()
    agent = _FakeAgent()  # must NOT run — quota blocks first

    async def _blocking_quota(_session: Any, _cell_id: UUID) -> QuotaStatus:
        raise CellQuotaExceeded("cell over hard cap")

    async def _noop_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        raise AssertionError("leaf_runner should not fire when quota blocks admission")

    with pytest.raises(CellQuotaExceeded):
        await execute_agent_task(
            task_id=task_id,
            cell_id=uuid4(),
            user_id=uuid4(),
            coordinator_agent=agent,  # type: ignore[arg-type]
            user_prompt="p",
            available_agent_slugs=["researcher"],
            leaf_runner=_noop_leaf,
            sse_publisher=publisher,
            session=session,  # type: ignore[arg-type]
            quota_admission=_blocking_quota,
        )

    assert task.status == "failed"
    assert agent.run_calls == []  # Coordinator never ran
    drained = publisher._drain.get(task_id, [])
    failed = [ev for ev in drained if ev.event_type == "task.failed"]
    assert len(failed) == 1
    assert failed[0].payload["error_code"] == "billing.cell_quota_exceeded"
    mock_emit.emit_task_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_quota_admission_soft_warn_emits_warning_and_succeeds(mock_emit: Any) -> None:
    """A soft-cap quota status emits task.budget_warning but does NOT block."""
    task_id = uuid4()
    task = _build_fake_task(task_id)
    session = _StubSession(task=task)
    publisher = InProcessSSEPublisher()
    agent = _FakeAgent()

    async def _soft_quota(_session: Any, _cell_id: UUID) -> QuotaStatus:
        return QuotaStatus(
            enforced=True,
            soft_warn=True,
            period_usage=Decimal("450"),
            soft_cap=Decimal("450"),
            hard_cap=Decimal("600"),
        )

    async def _noop_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        raise AssertionError("no delegation in this scenario")

    await execute_agent_task(
        task_id=task_id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=agent,  # type: ignore[arg-type]
        user_prompt="p",
        available_agent_slugs=["researcher"],
        leaf_runner=_noop_leaf,
        sse_publisher=publisher,
        session=session,  # type: ignore[arg-type]
        quota_admission=_soft_quota,
    )

    assert task.status == "succeeded"
    types = [ev.event_type for ev in publisher._drain.get(task_id, [])]
    assert types == ["task.started", "task.budget_warning", "task.completed"]
    warn = next(ev for ev in publisher._drain[task_id] if ev.event_type == "task.budget_warning")
    assert warn.payload["reason"] == "cell_soft_cap"
    assert warn.payload["period_usage_credits"] == "450"
