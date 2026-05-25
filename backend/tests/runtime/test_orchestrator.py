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
from src.runtime.orchestrator import OrchestratorContext, execute_agent_task
from src.runtime.sse_publisher import InProcessSSEPublisher
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
