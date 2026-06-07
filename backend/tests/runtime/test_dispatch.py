"""Unit tests for runtime.dispatch — inline orchestrator-dispatch wiring.

Phase 00.6 PR-B Commit 1. Covers the Wave-0 deterministic pipeline wiring
that closes the PR-A CRITICAL FINDING (POST /tasks queued-but-never-dispatched).

These tests inject fakes for the LLM layer + DB session so no Pydantic-AI
provider chain or real PostgreSQL is needed. The orchestrator itself is
covered by tests/runtime/test_orchestrator.py — here we test dispatch's own
seams: cost estimate, ScriptedCoordinator pipeline order, and the production
leaf-runner's child-task persistence + cost roll-in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.coordinator import CoordinatorOutput
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.runtime.dispatch import (
    CREDIT_PER_INPUT_TOKEN,
    CREDIT_PER_OUTPUT_TOKEN,
    ScriptedCoordinator,
    _extract_output_text,
    _extract_usage,
    _LeafSpec,
    build_leaf_runner,
    dispatch_task,
    estimate_credits,
)
from src.tasks.models import Task

# ── estimate_credits ──────────────────────────────────────────────────────


def test_estimate_credits_zero_tokens_is_zero() -> None:
    assert estimate_credits(input_tokens=0, output_tokens=0) == Decimal(0)


def test_estimate_credits_math_matches_constants() -> None:
    got = estimate_credits(input_tokens=1000, output_tokens=2000)
    expected = Decimal(1000) * CREDIT_PER_INPUT_TOKEN + Decimal(2000) * CREDIT_PER_OUTPUT_TOKEN
    assert got == expected


def test_estimate_credits_demo_scale_under_ac10_cap() -> None:
    """A realistic 3-specialist run (~30k in + ~20k out total) must stay
    well under the 30-credit (0.30 USD) AC10 cap."""
    cost = estimate_credits(input_tokens=30_000, output_tokens=20_000)
    assert cost < Decimal(30)


# ── ScriptedCoordinator ───────────────────────────────────────────────────


@dataclass
class _FakeDeps:
    runner: Any
    available_agent_slugs: list[str] = field(
        default_factory=lambda: ["researcher", "analyst", "writer"]
    )


@pytest.mark.asyncio
async def test_scripted_coordinator_drives_pipeline_in_order() -> None:
    calls: list[str] = []

    async def _runner(inp: DelegateInput, _deps: Any) -> DelegateResult:
        calls.append(inp.target_agent_slug)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output=f"{inp.target_agent_slug}-body",
            cost_credits=Decimal("1.0"),
            tokens_used=10,
        )

    coord = ScriptedCoordinator()
    deps = _FakeDeps(runner=_runner)
    result = await coord.run("market brief please", deps=deps)

    assert calls == ["researcher", "analyst", "writer"]
    assert isinstance(result.output, CoordinatorOutput)
    assert len(result.output.artifacts) == 3
    # Artifact kinds map per specialist.
    kinds = [a.type for a in result.output.artifacts]
    assert kinds == ["matrix", "analysis", "brief"]


@pytest.mark.asyncio
async def test_scripted_coordinator_chains_prior_output_into_sub_prompt() -> None:
    seen_prompts: list[str] = []

    async def _runner(inp: DelegateInput, _deps: Any) -> DelegateResult:
        seen_prompts.append(inp.sub_prompt)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output=f"OUT[{inp.target_agent_slug}]",
            cost_credits=Decimal(0),
            tokens_used=0,
        )

    coord = ScriptedCoordinator()
    await coord.run("исходный запрос", deps=_FakeDeps(runner=_runner))

    # researcher sees only the user prompt; analyst sees researcher output;
    # writer sees both prior outputs.
    assert "OUT[researcher]" not in seen_prompts[0]
    assert "OUT[researcher]" in seen_prompts[1]
    assert "OUT[researcher]" in seen_prompts[2]
    assert "OUT[analyst]" in seen_prompts[2]


# ── build_leaf_runner ─────────────────────────────────────────────────────


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeLeafOutput:
    body_markdown: str


@dataclass
class _FakeRunResult:
    _output: _FakeLeafOutput
    _usage: _FakeUsage

    @property
    def output(self) -> _FakeLeafOutput:
        return self._output

    def usage(self) -> _FakeUsage:
        return self._usage


class _FakeLeafAgent:
    def __init__(self, body: str, in_tok: int, out_tok: int) -> None:
        self._body = body
        self._in = in_tok
        self._out = out_tok
        self.run_prompts: list[str] = []

    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:
        self.run_prompts.append(prompt)
        return _FakeRunResult(
            _output=_FakeLeafOutput(body_markdown=self._body),
            _usage=_FakeUsage(input_tokens=self._in, output_tokens=self._out),
        )


@dataclass
class _FakeDeps2:
    pass


class _FakeSession:
    """Captures added rows + assigns ids on flush (mimics gen_random_uuid())."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


@pytest.mark.asyncio
async def test_build_leaf_runner_creates_child_task_and_costs() -> None:
    session = _FakeSession()
    parent_id = uuid4()
    cell_id = uuid4()
    user_id = uuid4()

    fake_agent = _FakeLeafAgent("исследование рынка", in_tok=1000, out_tok=2000)
    specs = {
        "researcher": _LeafSpec(
            build=lambda *, model: fake_agent,
            deps_factory=_FakeDeps2,
        )
    }

    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]  # never used — fake build ignores model
        session=session,  # type: ignore[arg-type]
        parent_task_id=parent_id,
        cell_id=cell_id,
        user_id=user_id,
        leaf_specs=specs,
    )

    result = await runner(
        DelegateInput(target_agent_slug="researcher", sub_prompt="изучи рынок"),
        None,  # type: ignore[arg-type]  # OrchestratorContext unused in production runner
    )

    assert result.output == "исследование рынка"
    assert result.tokens_used == 2000
    expected_cost = estimate_credits(input_tokens=1000, output_tokens=2000)
    assert result.cost_credits == expected_cost

    # A child Task row was persisted under the parent + cell.
    assert len(session.added) == 1
    child = session.added[0]
    assert child.parent_task_id == parent_id
    assert child.cell_id == cell_id
    assert child.initiated_by_user_id == user_id
    assert child.status == "succeeded"
    assert child.total_output_tokens == 2000
    assert isinstance(child.id, UUID)
    assert result.sub_task_id == child.id


@pytest.mark.asyncio
async def test_build_leaf_runner_unknown_slug_raises() -> None:
    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=_FakeSession(),  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        leaf_specs={},  # empty → any slug unknown
    )
    with pytest.raises(KeyError):
        await runner(
            DelegateInput(target_agent_slug="nonexistent", sub_prompt="x"),
            None,  # type: ignore[arg-type]
        )


# ── extract helpers (version-tolerant) ────────────────────────────────────


def test_extract_output_text_data_fallback_and_none() -> None:
    @dataclass
    class _OutOnlyData:
        data: Any

    @dataclass
    class _Body:
        body_markdown: str

    # .output missing → falls back to .data
    assert _extract_output_text(_OutOnlyData(data=_Body("from-data"))) == "from-data"

    # both missing → empty string
    @dataclass
    class _Empty:
        pass

    assert _extract_output_text(_Empty()) == ""


def test_extract_usage_request_response_aliases_and_none() -> None:
    @dataclass
    class _OldUsage:
        request_tokens: int
        response_tokens: int

    @dataclass
    class _OldResult:
        def usage(self) -> _OldUsage:
            return _OldUsage(request_tokens=7, response_tokens=11)

    assert _extract_usage(_OldResult()) == (7, 11)

    @dataclass
    class _NoUsage:
        pass

    assert _extract_usage(_NoUsage()) == (0, 0)


# ── dispatch_task wiring ──────────────────────────────────────────────────


class _DispatchSession:
    """Session shim for dispatch_task: get(Task) + add/flush."""

    def __init__(self, task: Task) -> None:
        self._task = task
        self.added: list[Any] = []

    async def get(self, _model: Any, _task_id: UUID) -> Task:
        return self._task

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


class _NoDelegationCoordinator:
    """Coordinator stand-in that returns directly without delegating —
    keeps dispatch_task's orchestrator path off the real LLM layer."""

    async def run(self, _user_prompt: str, *, deps: Any) -> Any:
        return _NoDelegationCoordinator._Result()

    @dataclass
    class _Result:
        output: CoordinatorOutput = field(
            default_factory=lambda: CoordinatorOutput(summary="scripted no-op")
        )


@pytest.mark.asyncio
async def test_dispatch_task_runs_orchestrator_and_returns_output() -> None:
    task_id = uuid4()
    task = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="parent",
        description="",
        status="queued",
        priority=5,
        input_jsonb={"prompt": "market brief"},
    )
    task.id = task_id
    task.total_cost_credits = Decimal(0)
    task.total_input_tokens = 0
    task.total_output_tokens = 0
    session = _DispatchSession(task)

    from src.runtime.sse_publisher import InProcessSSEPublisher

    publisher = InProcessSSEPublisher()

    result = await dispatch_task(
        task=task,
        session=session,  # type: ignore[arg-type]
        llm_router=object(),  # type: ignore[arg-type]  # never used — coordinator never delegates
        sse_publisher=publisher,
        coordinator=_NoDelegationCoordinator(),  # type: ignore[arg-type]
    )

    assert result["summary"] == "scripted no-op"
    assert task.status == "succeeded"
    drained = publisher._drain.get(task_id, [])
    assert [ev.event_type for ev in drained] == ["task.started", "task.completed"]
