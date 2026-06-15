"""AC-W1-16b — the real Coordinator agent runs plan-then-execute via PromptedOutput.

The Coordinator no longer carries the ``delegate_task`` tool; it emits the whole
``delegation_plan`` as one PromptedOutput JSON completion. These tests drive the
agent against the canned ``FakeLLMGatewayModel`` (no live keys) and assert the
fenced-JSON plan round-trips into a typed ``CoordinatorOutput``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.usage import RequestUsage
from src.agents.coordinator import (
    CoordinatorDeps,
    CoordinatorOutput,
    build_coordinator_agent,
)

from tests._fixtures.canned_pydantic_ai import FakeLLMGatewayModel


def _fenced(payload: dict[str, Any]) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


def _canned_model(payload: dict[str, Any], *, scenario: str = "plan_only") -> FakeLLMGatewayModel:
    model = FakeLLMGatewayModel(role_key="coordinator")
    model.set_response(
        "coordinator",
        scenario,
        [
            ModelResponse(
                parts=[TextPart(content=_fenced(payload))],
                usage=RequestUsage(input_tokens=50, output_tokens=80, details={}),
                model_name="fake",
                timestamp=datetime.now(UTC),
                finish_reason="stop",
            )
        ],
    )
    model.set_scenario(scenario)
    return model


async def test_coordinator_agent_emits_market_brief_plan():
    """A market-brief prompt yields the canonical researcher→analyst→writer plan."""
    plan = {
        "summary": "Декомпозиция на research → analyst → writer.",
        "delegation_plan": [
            {
                "step": 1,
                "agent": "researcher",
                "goal": "Собрать конкурентов и рынок",
                "status": "completed",
            },
            {
                "step": 2,
                "agent": "analyst",
                "goal": "Синтез и sizing",
                "status": "completed",
                "depends_on": [1],
            },
            {
                "step": 3,
                "agent": "writer",
                "goal": "Бриф ≥1500 слов + 10 постов",
                "status": "completed",
                "depends_on": [2],
            },
        ],
        "confidence": "high",
    }
    agent = build_coordinator_agent(model=_canned_model(plan))
    result = await agent.run(
        "Сделай маркет-бриф по AI-платформам для СМБ.",
        deps=CoordinatorDeps(cell_id=uuid4(), task_id=uuid4(), user_id=uuid4()),
    )

    assert isinstance(result.output, CoordinatorOutput)
    assert [s.agent for s in result.output.delegation_plan] == ["researcher", "analyst", "writer"]
    assert result.output.confidence == "high"


async def test_coordinator_agent_emits_non_brief_plan():
    """AC-W1-24: a non-market-brief prompt yields a differently-shaped plan
    (here a single rewrite step) — the agent is not hard-wired to the demo."""
    plan = {
        "summary": "Задача — переписать текст для лендинга, исследование не нужно.",
        "delegation_plan": [
            {
                "step": 1,
                "agent": "writer",
                "goal": "Переписать текст под лендинг",
                "status": "completed",
            },
        ],
        "confidence": "medium",
    }
    agent = build_coordinator_agent(model=_canned_model(plan))
    result = await agent.run(
        "Перепиши этот текст для лендинга.",
        deps=CoordinatorDeps(cell_id=uuid4(), task_id=uuid4(), user_id=uuid4()),
    )

    assert isinstance(result.output, CoordinatorOutput)
    assert [s.agent for s in result.output.delegation_plan] == ["writer"]
