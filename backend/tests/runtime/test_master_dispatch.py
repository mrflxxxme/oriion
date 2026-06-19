"""Master-Agent end-to-end through the REAL orchestrator (AC-W1-3.4 / 3.5).

Drives ``execute_agent_task`` with a ``MasterAgent`` whose inner Coordinator is
a real ``PlanExecutingCoordinator`` (canned plan) so leaf delegations flow
through the orchestrator's ``runner_with_orchestration`` — proving the Master's
own LLM calls AND the leaf delegations share ONE budget accumulator (the
50-credit cap covers the whole aggregate, R-32/R-04) and that
``task.total_cost_credits`` is the single cost authority (no double-count).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.coordinator import CoordinatorOutput, DelegationStep
from src.agents.master import MasterPlan
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.runtime.dispatch import MasterAgent, PlanExecutingCoordinator
from src.runtime.orchestrator import execute_agent_task
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.models import Task

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
    model: Any = None

    def __init__(self, plan: MasterPlan) -> None:
        self._plan = plan

    async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
        return _FakeRun(self._plan, _FakeUsage(10, 10))


class _FakeSynthAgent:
    model: Any = None

    def __init__(self, text: str) -> None:
        self._text = text

    async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
        return _FakeRun(self._text, _FakeUsage(10, 10))


@dataclass
class _PlanResult:
    output: CoordinatorOutput


class _FakeCoordinatorAgent:
    """Canned 3-step plan for the inner PlanExecutingCoordinator."""

    async def run(self, prompt: str, *, deps: Any) -> _PlanResult:
        return _PlanResult(
            output=CoordinatorOutput(
                summary="план",
                delegation_plan=[
                    DelegationStep(
                        step=1, agent="researcher", goal="r", status="p", artifact_type="matrix"
                    ),
                    DelegationStep(
                        step=2,
                        agent="analyst",
                        goal="a",
                        status="p",
                        artifact_type="analysis",
                        depends_on=[1],
                    ),
                    DelegationStep(
                        step=3,
                        agent="writer",
                        goal="w",
                        status="p",
                        artifact_type="brief",
                        depends_on=[2],
                    ),
                ],
            )
        )


class _DispatchSession:
    def __init__(self, task: Task) -> None:
        self._task = task
        self.added: list[Any] = []

    async def get(self, _model: Any, _id: UUID) -> Task:
        return self._task

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


def _build_master() -> MasterAgent:
    return MasterAgent(
        vertical_tag="agency_marketing_ru",
        plan_agent=_FakePlanAgent(MasterPlan(objective="кампания")),
        synthesis_agent=_FakeSynthAgent("# Финальный deliverable"),
        coordinator=PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent()),
    )


def _make_task() -> Task:
    task = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="parent",
        description="",
        status="queued",
        priority=5,
        input_jsonb={"prompt": "кампания"},
    )
    task.id = uuid4()
    task.total_cost_credits = Decimal(0)
    task.total_input_tokens = 0
    task.total_output_tokens = 0
    return task


@pytest.mark.asyncio
async def test_master_aggregate_cost_is_authority_no_double_count() -> None:
    """AC-W1-3.4: task.total = 2 master calls + 3 leaf delegations, each once."""
    task = _make_task()
    session = _DispatchSession(task)
    publisher = InProcessSSEPublisher()

    async def _leaf_runner(inp: DelegateInput, _ctx: Any) -> DelegateResult:
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output="x",
            cost_credits=Decimal("1"),
            tokens_used=5,
            input_tokens=3,
        )

    async def _master_biller(_session: Any, billing: Any) -> Decimal:
        return Decimal("2")

    result = await execute_agent_task(
        task_id=task.id,
        cell_id=task.cell_id,
        user_id=task.initiated_by_user_id,
        coordinator_agent=_build_master(),  # type: ignore[arg-type]
        user_prompt="кампания",
        available_agent_slugs=["researcher", "analyst", "writer"],
        leaf_runner=_leaf_runner,
        sse_publisher=publisher,
        session=session,  # type: ignore[arg-type]
        master_step_recorder=_master_biller,
    )

    assert task.status == "succeeded"
    # 2 (plan) + 1*3 (leaves) + 2 (synthesis) = 7 — each counted exactly once.
    assert task.total_cost_credits == Decimal("7")
    assert result["final_artifact_markdown"] == "# Финальный deliverable"

    events = [ev.event_type for ev in publisher._drain.get(task.id, [])]
    assert events[0] == "task.started"
    assert events[-1] == "task.completed"
    assert events.count("task.delegation_completed") == 3
    # The 2 Master calls surface as step_completed events.
    assert events.count("task.step_completed") == 2


@pytest.mark.asyncio
async def test_master_aggregate_trips_budget_cap() -> None:
    """AC-W1-3.5: a Master call that pushes the aggregate over 50 credits raises
    BudgetExceeded → the task ends 'failed' (cap covers Master + children)."""
    task = _make_task()
    session = _DispatchSession(task)
    publisher = InProcessSSEPublisher()

    async def _leaf_runner(inp: DelegateInput, _ctx: Any) -> DelegateResult:
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output="x",
            cost_credits=Decimal("1"),
            tokens_used=5,
            input_tokens=3,
        )

    async def _expensive_master_biller(_session: Any, billing: Any) -> Decimal:
        return Decimal("60")  # the very first Master (plan) call blows the cap

    with pytest.raises(Exception):  # noqa: B017 — BudgetExceeded bubbles via the agent run
        await execute_agent_task(
            task_id=task.id,
            cell_id=task.cell_id,
            user_id=task.initiated_by_user_id,
            coordinator_agent=_build_master(),  # type: ignore[arg-type]
            user_prompt="кампания",
            available_agent_slugs=["researcher", "analyst", "writer"],
            leaf_runner=_leaf_runner,
            sse_publisher=publisher,
            session=session,  # type: ignore[arg-type]
            master_step_recorder=_expensive_master_biller,
        )

    assert task.status == "failed"
    events = [ev.event_type for ev in publisher._drain.get(task.id, [])]
    assert "task.failed" in events


# ── resolve_master (vertical detection) ───────────────────────────────────


def test_resolve_master_none_vertical_returns_none() -> None:
    from src.runtime.dispatch import resolve_master

    assert resolve_master(None, llm_router=object()) is None  # type: ignore[arg-type]
    assert resolve_master("", llm_router=object()) is None  # type: ignore[arg-type]


def test_resolve_master_missing_prompt_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A vertical without a masters/ prompt falls back to single-layer (None)."""
    from src.agents.exceptions import RolePromptParseError
    from src.runtime import dispatch

    def _raise(_vertical: str) -> Any:
        raise RolePromptParseError("not found")

    monkeypatch.setattr(dispatch, "load_master_prompt", _raise)
    assert dispatch.resolve_master("wb_seller", llm_router=object()) is None  # type: ignore[arg-type]


def test_resolve_master_builds_master_when_prompt_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.agents.services.role_prompt_loader import RolePrompt
    from src.runtime import dispatch

    prompt = RolePrompt(
        role_id="master-agency-marketing-ru",
        version="0.1.0",
        status="reviewed",
        model_default="deepseek-chat",
        preset="",
        contract_type="role-prompt",
        language="ru",
        frontmatter={},
        sections={},
        raw_text="# Master\n\nТы — Master.",
    )
    monkeypatch.setattr(dispatch, "load_master_prompt", lambda _v: prompt)
    master = dispatch.resolve_master("agency_marketing_ru", llm_router=object())  # type: ignore[arg-type]
    assert isinstance(master, MasterAgent)
    assert master._vertical_tag == "agency_marketing_ru"


# ── MasterAgent production-build branches ─────────────────────────────────


def _role_prompt() -> Any:
    from src.agents.services.role_prompt_loader import RolePrompt

    return RolePrompt(
        role_id="master-agency-marketing-ru",
        version="0.1.0",
        status="draft",
        model_default="deepseek-chat",
        preset="",
        contract_type="role-prompt",
        language="ru",
        frontmatter={},
        sections={},
        raw_text="# Master\n\ntext",
    )


def test_master_ensure_agents_builds_real_agents_and_models() -> None:
    master = MasterAgent(
        vertical_tag="agency_marketing_ru", llm_router=object(), master_prompt=_role_prompt()
    )
    plan_agent, plan_model, synth_agent, synth_model = master._ensure_agents()
    assert plan_agent is not None
    assert synth_agent is not None
    assert plan_model is not None and synth_model is not None


def test_master_coordinator_for_builds_default_plan_executor() -> None:
    master = MasterAgent(vertical_tag="agency_marketing_ru", llm_router=object())
    assert isinstance(master._coordinator_for(), PlanExecutingCoordinator)


def test_master_ensure_agents_requires_router_or_injected_agents() -> None:
    master = MasterAgent(vertical_tag="agency_marketing_ru")
    with pytest.raises(ValueError, match="injected agents"):
        master._ensure_agents()


@pytest.mark.asyncio
async def test_dispatch_task_routes_marketing_cell_through_master(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dispatch_task: a vertical cell → Master path + master_step_recorder wired."""
    from src.agents.coordinator import CoordinatorOutput
    from src.agents.master import MasterResponse
    from src.multitenancy.models import Cell
    from src.runtime import dispatch

    cell = Cell(
        workspace_id=uuid4(),
        slug="c",
        display_name="C",
        vertical_template_slug="agency_marketing_ru",
    )
    cell.id = uuid4()
    task = _make_task()
    task.cell_id = cell.id

    class _RoutingSession:
        def __init__(self) -> None:
            self.added: list[Any] = []

        async def get(self, model: Any, _id: UUID) -> Any:
            return cell if model is Cell else task

        def add(self, obj: Any) -> None:
            self.added.append(obj)

        async def flush(self) -> None:
            for obj in self.added:
                if getattr(obj, "id", None) is None:
                    obj.id = uuid4()

    captured: dict[str, Any] = {}

    class _FakeMaster:
        async def run(self, prompt: str, *, deps: Any) -> Any:
            captured["master_recorder"] = deps.master_recorder
            return _MasterRunResultStub(
                MasterResponse(
                    summary="s",
                    final_artifact_markdown="итоговый артефакт",
                    coordinator_output=CoordinatorOutput(summary="s"),
                )
            )

    @dataclass
    class _MasterRunResultStub:
        output: Any

    monkeypatch.setattr(
        dispatch, "resolve_master", lambda _v, *, llm_router, workspace_id=None: _FakeMaster()
    )
    publisher = InProcessSSEPublisher()
    result = await dispatch.dispatch_task(
        task=task,
        session=_RoutingSession(),  # type: ignore[arg-type]
        llm_router=object(),  # type: ignore[arg-type]
        sse_publisher=publisher,
    )

    # Master path taken → orchestrator wired the ctx-aware master_recorder on deps.
    assert captured["master_recorder"] is not None
    assert result["final_artifact_markdown"] == "итоговый артефакт"
    assert task.status == "succeeded"
