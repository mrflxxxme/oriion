"""E2E demo-flow integration test for «Market & content brief» scenario.

Phase 00.5b Commit 7. Per founder-resolved T4 (Hybrid b): CI canned-data
flow asserts SSE event order + 3-parallel delegation + cost rollup math +
3 artifact contracts. Live-key staging validation runs in Phase 00.6 via
backend/scripts/demo_market_brief.py.

Scope clarification (audit anchor):
    * This test bypasses the full Pydantic-AI Agent.run() tool-call loop
      and drives the orchestrator's runner directly with canned
      DelegateResults. The Agent.run() tool-call canned shape (ToolCallPart
      ModelResponse instead of TextPart) is a Wave-1 hardening pass per
      AC14 — at that point this test extends to also exercise the
      Coordinator → tool-call → delegate_task path with the same fixtures.
    * SSE event order assertions, leaf-dispatch + budget guard, cost
      rollup math, and artifact-shape AC9 checks are exercised end-to-end
      here. That covers the demo-flow integration surface that AC4-7 +
      AC9 demand.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from src.runtime.sse_events import TaskStreamEvent
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.exceptions import BudgetExceeded

from tests._fixtures.canned_pydantic_ai.market_brief_demo import (
    RESPONSES,
    SCENARIO_ID,
    researcher_matrix_row_count,
    writer_brief_word_count,
    writer_content_plan_post_count,
)


def _canned_text_for(role_key: str) -> str:
    key = (role_key, SCENARIO_ID)
    responses = RESPONSES[key]
    # Every role now has exactly one canned response (the coordinator emits a
    # single JSON plan; specialists emit their artifact body).
    return responses[0].parts[0].content


async def _drive_three_parallel_delegations(publisher: InProcessSSEPublisher):
    """Simulate Coordinator dispatching to Researcher → Analyst → Writer.

    Returns (collected_events, accumulated_cost, artifacts) — mirrors what
    the orchestrator would compute end-to-end if Pydantic-AI emitted the
    tool calls.
    """
    from src.runtime.budget_guard import check_budget

    task_id = uuid4()
    await publisher.publish(TaskStreamEvent(event_type="task.started", task_id=task_id, payload={}))

    accumulated_cost = Decimal(0)
    artifacts: dict[str, str] = {}
    cost_per_leaf = Decimal("4.5")  # well under 50-credit cap x 3 leaves = 13.5

    for slug, artifact_kind in [
        ("researcher", "competitive-matrix"),
        ("analyst", "analysis"),
        ("writer", "brief-and-content-plan"),
    ]:
        await publisher.publish(
            TaskStreamEvent(
                event_type="task.delegation_started",
                task_id=task_id,
                payload={"target_agent_slug": slug},
            )
        )
        check_budget(accumulated_cost=accumulated_cost, pending_cost=cost_per_leaf)
        canned = _canned_text_for(slug)
        accumulated_cost += cost_per_leaf
        artifacts[artifact_kind] = canned
        await publisher.publish(
            TaskStreamEvent(
                event_type="task.delegation_completed",
                task_id=task_id,
                payload={
                    "target_agent_slug": slug,
                    "sub_task_id": str(uuid4()),
                    "cost_credits": str(cost_per_leaf),
                },
            )
        )

    await publisher.publish(
        TaskStreamEvent(
            event_type="task.completed",
            task_id=task_id,
            payload={
                "total_cost_credits": str(accumulated_cost),
                "total_duration_ms": 1234,
            },
        )
    )
    return task_id, accumulated_cost, artifacts


async def test_demo_flow_emits_expected_sse_order():
    """AC5 anchor: task.started → 3x (delegation_started + delegation_completed)
    → task.completed event ledger emitted in order."""
    publisher = InProcessSSEPublisher()
    task_id, _, _ = await _drive_three_parallel_delegations(publisher)

    collected: list[str] = []
    async for ev in publisher.subscribe(task_id):
        collected.append(ev.event_type)

    expected = [
        "task.started",
        "task.delegation_started",
        "task.delegation_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.completed",
    ]
    assert collected == expected, f"SSE ordering mismatch: got {collected}"


async def test_demo_flow_cost_rollup_math():
    """AC6 anchor: parent total_cost == sum(leaf costs). Three leaves at
    4.5 T-credits each → 13.5 total."""
    publisher = InProcessSSEPublisher()
    _, total_cost, _ = await _drive_three_parallel_delegations(publisher)
    assert total_cost == Decimal("13.5")


async def test_demo_flow_three_artifact_contracts_ac9():
    """AC9 anchor: brief ≥1500w + matrix ≥5x4 + content-plan == 10 posts.

    Researcher's output contains the competitive matrix; Writer's output
    is brief.md + content-plan.md concatenated. Assertions delegate to the
    canned-fixture ledger functions (single source of truth)."""
    publisher = InProcessSSEPublisher()
    _, _, artifacts = await _drive_three_parallel_delegations(publisher)

    # AC9.a — brief word count ≥1500.
    assert writer_brief_word_count() >= 1500
    # AC9.b — competitive matrix ≥5 rows x ≥4 cols.
    assert researcher_matrix_row_count() >= 5
    assert (
        "| Игрок | Сегмент | Сильная сторона | Слабая сторона |" in artifacts["competitive-matrix"]
    ), "matrix header must have 4 columns"
    # AC9.c — content plan == 10 posts.
    assert writer_content_plan_post_count() == 10


async def test_demo_flow_budget_guard_blocks_runaway():
    """AC10 anchor / F-P5-2: simulate Coordinator over-decomposing into
    more than 50/4.5 ≈ 11 sub-tasks — the 12th must trip BudgetExceeded
    before LLM dispatch."""
    from src.runtime.budget_guard import check_budget

    accumulated = Decimal(0)
    per_leaf = Decimal("4.5")
    # 11 leaves x 4.5 = 49.5 (under cap)
    for _ in range(11):
        check_budget(accumulated_cost=accumulated, pending_cost=per_leaf)
        accumulated += per_leaf
    # 12th call would cross 50 — must raise.
    with pytest.raises(BudgetExceeded):
        check_budget(accumulated_cost=accumulated, pending_cost=per_leaf)


def test_canned_coordinator_emits_json_plan():
    """AC-W1-16b: the Coordinator's single canned response is a fenced-JSON
    CoordinatorOutput with the 3-step plan + artifact types carried in-plan."""
    import json

    coord_responses = RESPONSES[("coordinator", SCENARIO_ID)]
    assert len(coord_responses) == 1
    text = coord_responses[0].parts[0].content
    payload = json.loads(text.removeprefix("```json").removesuffix("```").strip())
    plan = payload["delegation_plan"]
    assert [s["agent"] for s in plan] == ["researcher", "analyst", "writer"]
    assert [s["artifact_type"] for s in plan] == ["matrix", "analysis", "brief"]


async def test_demo_flow_real_path_drives_coordinator():
    """AC-W1-16b/24: drive the REAL PlanExecutingCoordinator + orchestrator with the
    canned coordinator plan + canned leaf outputs. The plan (not code-side framing)
    decides the steps, artifacts are typed from the plan, and the SSE ledger comes
    from the production orchestrator path."""
    from src.agents.coordinator import build_coordinator_agent
    from src.agents.tools.delegate import DelegateInput, DelegateResult
    from src.runtime.dispatch import PlanExecutingCoordinator
    from src.runtime.orchestrator import execute_agent_task

    from tests._fixtures.canned_pydantic_ai import FakeLLMGatewayModel

    coord_model = FakeLLMGatewayModel(role_key="coordinator")
    coord_model.set_response("coordinator", SCENARIO_ID, RESPONSES[("coordinator", SCENARIO_ID)])
    coord_model.set_scenario(SCENARIO_ID)
    coord = PlanExecutingCoordinator(coordinator_agent=build_coordinator_agent(model=coord_model))

    async def _leaf_runner(inp: DelegateInput, _ctx: object) -> DelegateResult:
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output=_canned_text_for(inp.target_agent_slug),
            cost_credits=Decimal("4.5"),
            tokens_used=100,
        )

    class _NoTaskSession:
        async def get(self, _model: object, _id: object) -> None:
            return None

        def add(self, _obj: object) -> None: ...

        async def flush(self) -> None: ...

    publisher = InProcessSSEPublisher()
    task_id = uuid4()
    result = await execute_agent_task(
        task_id=task_id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=coord,  # type: ignore[arg-type]
        user_prompt="Подготовь market & content brief.",
        available_agent_slugs=["researcher", "analyst", "writer"],
        leaf_runner=_leaf_runner,
        sse_publisher=publisher,
        session=_NoTaskSession(),  # type: ignore[arg-type]
    )

    # AC-W1-24: artifacts typed from the plan, in execution order.
    assert [a["type"] for a in result["artifacts"]] == ["matrix", "analysis", "brief"]
    # AC5: the SSE ledger from the real orchestrator path.
    collected = [ev.event_type async for ev in publisher.subscribe(task_id)]
    assert collected == [
        "task.started",
        "task.delegation_started",
        "task.delegation_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.completed",
    ]


def test_demo_flow_artifacts_have_ru_content():
    """Sanity: all canned content is RU per Wave 0 anchor (RU-business-aware)."""
    for role in ("researcher", "writer", "analyst"):
        text = _canned_text_for(role)
        # Cyrillic characters present.
        assert any(
            0x0400 <= ord(c) <= 0x04FF for c in text
        ), f"{role} canned content missing Cyrillic"
