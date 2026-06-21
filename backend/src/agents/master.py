"""Master-Agent schemas + agent factories (ADR-029, AC-W1-3).

The Master-Agent is the vertical "CEO": it interprets the user message through
a domain lens (``MasterPlan``), delegates the operational objective to the
subordinate Coordinator (the "COO"), then synthesizes the team's output into a
domain-quality-checked deliverable (``MasterResponse``).

This module is the **agents-layer** half: pure schemas + Pydantic-AI agent
factories, no runtime/dispatch import (so ``runtime`` may import it without a
cycle). The orchestration object that wires a Master above a
``PlanExecutingCoordinator`` lives in ``runtime.dispatch.MasterAgent``.

Model split (grill 2026-06-19, refines ADR-029 §model-by-wave against code
reality): the **plan** call needs structured JSON (``MasterPlan``) so it runs on
``deepseek-chat`` (``role_key='master'``) — ``deepseek-reasoner``/R1 emits
reasoning prose that breaks fenced-JSON, the same reason it was pulled off the
Coordinator. The **synthesis** call is free-text, so it runs on R1
(``role_key='master_synthesis'``) where its reasoning depth pays off.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, PromptedOutput

from src.agents.coordinator import CoordinatorOutput
from src.agents.services.role_prompt_loader import RolePrompt
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

# Router role-keys (mapped in llm_gateway.services.router_service.ROLE_TO_MODEL).
ROLE_KEY_PLAN = "master"
ROLE_KEY_SYNTHESIS = "master_synthesis"


# ── structured output of the Master's first (plan) LLM call ───────────────


class MasterPlan(BaseModel):
    """The Master's strategic interpretation of the user message.

    The LLM produces only the *content* (objective + domain framing); the
    deterministic ``vertical_tag`` + ``parent_task_id`` are supplied by the
    runtime when it assembles the ``StrategicContext`` (the LLM never invents
    those).
    """

    objective: str = Field(..., min_length=1)
    domain_constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    rationale: str = ""


# ── user-facing result of the whole Master run ────────────────────────────


class MasterResponse(BaseModel):
    """Master-Agent's final, user-facing deliverable (ADR-029).

    Reuses the Coordinator's ``CoordinatorOutput`` verbatim as the embedded
    operational result (grill decision #3 — no separate Coordinator→Master
    envelope); the Master adds the domain-quality synthesis on top.
    """

    summary: str
    final_artifact_markdown: str
    domain_quality_passed: bool = True
    domain_quality_notes: list[str] = Field(default_factory=list)
    coordinator_output: CoordinatorOutput
    confidence: str = "medium"  # 'high' | 'medium' | 'low'
    # NOTE: the aggregate cost authority is the orchestrator step-sum
    # (task.total_cost_credits + the SSE result dict's top-level
    # total_cost_credits) — the Master cannot compute the leaf+Master aggregate
    # at construction, so this model carries no (stale-zero) cost field.


# ── per-run deps for the Master's own Pydantic-AI agents ──────────────────


@dataclass
class MasterDeps:
    """Minimal deps for the Master's own LLM agents (plan + synthesis).

    The Master agents carry no tools, so this is mostly identity context;
    Pydantic-AI still requires a ``deps_type``.
    """

    cell_id: UUID
    task_id: UUID
    user_id: UUID
    vertical_tag: str


# ── billing payload + recorder port for the Master's own LLM calls ────────


@dataclass(frozen=True)
class MasterCallBilling:
    """Everything the recorder needs to bill + persist one Master LLM call.

    A Master call is persisted as a ``task_steps`` row (``step_type='llm_call'``)
    on the Master (parent) task — distinct from the leaf ``delegation`` steps —
    so the per-delegation ledger (AC-W1-2/13) also captures the Master overhead
    that R-32 flags (+15-20% tokens per vertical task).
    """

    parent_task_id: UUID
    cell_id: UUID
    user_id: UUID
    vertical_tag: str  # resolves the master archetype FK for the task_steps row
    phase: str  # 'plan' | 'synthesis'
    step_index: int
    provider_slug: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


# A recorder bills one Master LLM call + returns its cost in credits. The
# runtime orchestrator wraps the session-bound biller into this ctx-aware port
# (budget accumulate + cap check + SSE), symmetric to the leaf ``DelegateRunner``.
MasterCallRecorder = Callable[[MasterCallBilling], Awaitable[Decimal]]


# ── agent factories ───────────────────────────────────────────────────────


def build_master_plan_agent(
    *,
    model: LLMGatewayModel,
    master_prompt: RolePrompt,
) -> Agent[MasterDeps, MasterPlan]:
    """Construct the Master's strategic-plan agent (structured JSON output).

    Runs on ``deepseek-chat`` (``role_key='master'``) via ``PromptedOutput`` so
    the strategic interpretation returns a parseable ``MasterPlan``.
    """
    return Agent(
        model=model,
        deps_type=MasterDeps,
        output_type=PromptedOutput(MasterPlan),
        system_prompt=master_prompt.composed_system_prompt(),
        tools=[],
    )


def build_master_synthesis_agent(
    *,
    model: LLMGatewayModel,
    master_prompt: RolePrompt,
) -> Agent[MasterDeps, str]:
    """Construct the Master's synthesis agent (free-text markdown output).

    Runs on ``deepseek-reasoner``/R1 (``role_key='master_synthesis'``): the
    final domain-quality synthesis is prose, so R1's reasoning depth applies and
    the fenced-JSON fragility does not.
    """
    return Agent(
        model=model,
        deps_type=MasterDeps,
        output_type=str,
        system_prompt=master_prompt.composed_system_prompt(),
        tools=[],
    )


__all__ = [
    "ROLE_KEY_PLAN",
    "ROLE_KEY_SYNTHESIS",
    "MasterCallBilling",
    "MasterCallRecorder",
    "MasterDeps",
    "MasterPlan",
    "MasterResponse",
    "build_master_plan_agent",
    "build_master_synthesis_agent",
]
