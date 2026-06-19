"""Unit tests for the Master-Agent layer (ADR-029, AC-W1-3).

Exercises the agents-layer factories (``build_master_*_agent``) + the runtime
orchestration object (``runtime.dispatch.MasterAgent``) with injected fakes so
no real provider chain or PG is needed. The end-to-end aggregate-budget +
cost-authority claims (AC-W1-3.4/3.5) are covered against the real orchestrator
in ``tests/runtime/test_master_dispatch.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.coordinator import ArtifactRef, CoordinatorOutput
from src.agents.master import (
    MasterCallBilling,
    MasterPlan,
    MasterResponse,
    build_master_plan_agent,
    build_master_synthesis_agent,
)
from src.agents.services.role_prompt_loader import RolePrompt
from src.runtime.dispatch import MasterAgent
from src.tasks.exceptions import BudgetExceeded

# ── fakes ──────────────────────────────────────────────────────────────────


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeRun:
    output: Any
    _usage: _FakeUsage

    def usage(self) -> _FakeUsage:
        return self._usage


class _FakePlanAgent:
    def __init__(self, plan: MasterPlan, *, in_tok: int = 100, out_tok: int = 50) -> None:
        self.plan = plan
        self._in = in_tok
        self._out = out_tok
        self.prompts: list[str] = []
        self.model: Any = None  # billing → provider/model "" via getattr default

    async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
        self.prompts.append(prompt)
        return _FakeRun(self.plan, _FakeUsage(self._in, self._out))


class _FakeSynthAgent:
    def __init__(self, text: str, *, in_tok: int = 200, out_tok: int = 300) -> None:
        self.text = text
        self._in = in_tok
        self._out = out_tok
        self.prompts: list[str] = []
        self.model: Any = None

    async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
        self.prompts.append(prompt)
        return _FakeRun(self.text, _FakeUsage(self._in, self._out))


@dataclass
class _CoordRun:
    output: CoordinatorOutput


class _FakeCoordinator:
    def __init__(self, output: CoordinatorOutput) -> None:
        self._output = output
        self.calls: list[tuple[str, Any]] = []

    async def run(self, objective: str, *, deps: Any) -> _CoordRun:
        self.calls.append((objective, deps))
        return _CoordRun(self._output)


class _RecorderStub:
    """Stand-in for the orchestrator's ctx-aware master_recorder."""

    def __init__(self, *, raise_on_phase: str | None = None, cost: Decimal = Decimal("1")) -> None:
        self.billings: list[MasterCallBilling] = []
        self._raise_on = raise_on_phase
        self._cost = cost

    async def __call__(self, billing: MasterCallBilling) -> Decimal:
        self.billings.append(billing)
        if self._raise_on is not None and billing.phase == self._raise_on:
            raise BudgetExceeded(f"over cap on {billing.phase}")
        return self._cost


@dataclass
class _DepsStub:
    runner: Any = None
    master_recorder: Any = None
    cell_id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    available_agent_slugs: list[str] = field(
        default_factory=lambda: ["researcher", "analyst", "writer"]
    )
    current_depth: int = 0
    max_delegation_depth: int = 5


def _coordinator_output() -> CoordinatorOutput:
    return CoordinatorOutput(
        summary="Команда подготовила матрицу + анализ + бриф.",
        artifacts=[
            ArtifactRef(id="a1", type="matrix", path_or_inline="## матрица"),
            ArtifactRef(id="a2", type="analysis", path_or_inline="## анализ"),
            ArtifactRef(id="a3", type="brief", path_or_inline="## бриф"),
        ],
        confidence="high",
    )


def _plan() -> MasterPlan:
    return MasterPlan(
        objective="Подготовить кампанию для клиента под РФ-рынок",
        domain_constraints=["бюджет ≤ 50к"],
        success_criteria=["≥3 креатива"],
        rationale="клиентский кейс",
    )


def _master(
    *, plan: MasterPlan, synth_text: str, coord_out: CoordinatorOutput
) -> tuple[MasterAgent, _FakePlanAgent, _FakeSynthAgent, _FakeCoordinator]:
    plan_agent = _FakePlanAgent(plan)
    synth_agent = _FakeSynthAgent(synth_text)
    coord = _FakeCoordinator(coord_out)
    master = MasterAgent(
        vertical_tag="agency_marketing_ru",
        plan_agent=plan_agent,
        synthesis_agent=synth_agent,
        coordinator=coord,
    )
    return master, plan_agent, synth_agent, coord


# ── factories ────────────────────────────────────────────────────────────


def _role_prompt() -> RolePrompt:
    return RolePrompt(
        role_id="master-agency-marketing-ru",
        version="0.1.0",
        status="reviewed",
        model_default="deepseek-chat",
        preset="",
        contract_type="role-prompt",
        language="ru",
        frontmatter={},
        sections={},
        raw_text="# Master\n\nТы — Master-Agent вертикали.",
    )


def test_build_master_plan_and_synthesis_agents_smoke() -> None:
    from tests._fixtures.canned_pydantic_ai.fake_model import FakeLLMGatewayModel

    prompt = _role_prompt()
    plan_agent = build_master_plan_agent(model=FakeLLMGatewayModel("master"), master_prompt=prompt)
    synth_agent = build_master_synthesis_agent(
        model=FakeLLMGatewayModel("master_synthesis"), master_prompt=prompt
    )
    assert plan_agent is not None
    assert synth_agent is not None


# ── MasterAgent.run ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_master_run_produces_master_response_with_artifact() -> None:
    """AC-W1-3.6: a Master run yields a MasterResponse with a non-empty deliverable."""
    master, _plan_agent, _synth, _coord = _master(
        plan=_plan(),
        synth_text="# Финальный план\n\nГотовый deliverable.",
        coord_out=_coordinator_output(),
    )
    deps = _DepsStub(master_recorder=_RecorderStub())
    result = await master.run("Нужна кампания", deps=deps)

    assert isinstance(result.output, MasterResponse)
    assert result.output.final_artifact_markdown == "# Финальный план\n\nГотовый deliverable."
    assert result.output.domain_quality_passed is True
    # The Coordinator's operational output is embedded verbatim (grill #3).
    assert result.output.coordinator_output.summary.startswith("Команда подготовила")
    assert result.output.confidence == "high"


@pytest.mark.asyncio
async def test_master_run_assembles_strategic_context_for_coordinator() -> None:
    """AC-W1-3.2/3.3: the Master hands the Coordinator a StrategicContext whose
    objective comes from the plan + parent_task_id chains under the Master task."""
    master, _plan_agent, _synth, coord = _master(
        plan=_plan(), synth_text="deliverable", coord_out=_coordinator_output()
    )
    deps = _DepsStub(master_recorder=_RecorderStub())
    await master.run("Нужна кампания", deps=deps)

    objective, inner_deps = coord.calls[0]
    assert objective == "Подготовить кампанию для клиента под РФ-рынок"
    assert inner_deps.strategic_context is not None
    assert inner_deps.strategic_context.parent_task_id == deps.task_id
    assert inner_deps.strategic_context.vertical_tag == "agency_marketing_ru"
    assert inner_deps.strategic_context.domain_constraints == ["бюджет ≤ 50к"]
    # The same leaf runner is reused so leaf delegations chain under the Master.
    assert inner_deps.runner is deps.runner


@pytest.mark.asyncio
async def test_master_run_bills_both_master_calls() -> None:
    """Both Master LLM calls (plan + synthesis) are billed via the recorder with
    a collision-free step-index space vs the leaf delegation steps (1..N)."""
    recorder = _RecorderStub()
    master, _plan_agent, _synth, _coord = _master(
        plan=_plan(), synth_text="deliverable", coord_out=_coordinator_output()
    )
    await master.run("Нужна кампания", deps=_DepsStub(master_recorder=recorder))

    phases = [b.phase for b in recorder.billings]
    assert phases == ["plan", "synthesis"]
    # plan → step 0; synthesis → len(artifacts)+1 = 4 (leaves occupy 1..3).
    assert recorder.billings[0].step_index == 0
    assert recorder.billings[1].step_index == 4
    assert all(b.vertical_tag == "agency_marketing_ru" for b in recorder.billings)
    assert recorder.billings[1].input_tokens == 200  # synthesis usage threaded through


@pytest.mark.asyncio
async def test_master_run_propagates_budget_exceeded_from_recorder() -> None:
    """AC-W1-3.5: a BudgetExceeded raised mid-run (aggregate cap) propagates —
    the Master does not swallow it, so the orchestrator stamps the task failed."""
    recorder = _RecorderStub(raise_on_phase="synthesis")
    master, _plan_agent, _synth, _coord = _master(
        plan=_plan(), synth_text="deliverable", coord_out=_coordinator_output()
    )
    with pytest.raises(BudgetExceeded):
        await master.run("Нужна кампания", deps=_DepsStub(master_recorder=recorder))


@pytest.mark.asyncio
async def test_master_run_without_recorder_skips_billing() -> None:
    """No master_recorder on deps → run still completes (billing is a no-op)."""
    master, _plan_agent, _synth, _coord = _master(
        plan=_plan(), synth_text="deliverable", coord_out=_coordinator_output()
    )
    result = await master.run("Нужна кампания", deps=_DepsStub(master_recorder=None))
    assert isinstance(result.output, MasterResponse)


@pytest.mark.asyncio
async def test_master_run_rejects_non_master_plan_output() -> None:
    """A plan agent that returns the wrong type fails loudly (not silently)."""

    class _BadPlanAgent:
        model: Any = None

        async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
            return _FakeRun("not a MasterPlan", _FakeUsage(1, 1))

    master = MasterAgent(
        vertical_tag="agency_marketing_ru",
        plan_agent=_BadPlanAgent(),
        synthesis_agent=_FakeSynthAgent("x"),
        coordinator=_FakeCoordinator(_coordinator_output()),
    )
    with pytest.raises(TypeError):
        await master.run("x", deps=_DepsStub(master_recorder=_RecorderStub()))


@pytest.mark.asyncio
async def test_master_quality_check_flags_empty_synthesis() -> None:
    """Soft Wave-1 quality flag: an empty deliverable → domain_quality_passed False."""
    master, _plan_agent, _synth, _coord = _master(
        plan=_plan(), synth_text="   ", coord_out=_coordinator_output()
    )
    result = await master.run("Нужна кампания", deps=_DepsStub(master_recorder=_RecorderStub()))
    assert result.output.domain_quality_passed is False
    assert result.output.domain_quality_notes
