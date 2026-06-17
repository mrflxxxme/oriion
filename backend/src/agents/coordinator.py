"""Coordinator — top-level orchestrator of the productivity-core preset.

Wave 0: horizontal preset, no Master-Agent layer above. The Coordinator
produces a delegation plan over the leaf specialists (Researcher, Writer,
Analyst), which cannot delegate themselves (per ADR-016 team-first UX).

AC-W1-16b/24: the Coordinator runs **plan-then-execute** via Pydantic-AI
``PromptedOutput`` — it returns the whole ``delegation_plan`` as one JSON
completion (no function-calling, robust across all providers), and
``runtime.dispatch.PlanExecutingCoordinator`` executes each step, re-applying
the ``delegate_task`` depth/slug guards. ``delegate_task`` itself is retained
for the shared guard helper + the DelegateInput/DelegateResult contracts.

Per phase-spec 00.5 inline definition + ADR-022 (Coordinator top-level in
horizontal preset) + ADR-023/024 plan-then-execute amendment.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, PromptedOutput

from src.agents.services.role_prompt_loader import RolePrompt, load_role_prompt
from src.agents.tools.delegate import (
    CoordinatorDeps,
    DelegateInput,
    DelegateResult,
)
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

ROLE_KEY = "coordinator"


# ── output schema (structured Pydantic-AI output) ───────────────────────
#
# AC-W1-7: the per-run deps container ``CoordinatorDeps`` is now defined once
# in ``agents/tools/delegate.py`` (the low-level module, to avoid an import
# cycle) and re-exported here for backwards-compatible imports.


class Citation(BaseModel):
    url: str
    accessed: str | None = None
    claim: str = ""


class ArtifactRef(BaseModel):
    id: str
    type: str  # 'brief' | 'matrix' | 'content-plan' | 'analysis'
    path_or_inline: str = ""


class DelegationStep(BaseModel):
    step: int
    agent: str
    goal: str
    status: str  # 'completed' | 'skipped' | 'failed'
    # AC-W1-24: the Coordinator names each step's artifact type (e.g. 'matrix',
    # 'analysis', 'brief', 'landing-copy'), so artifact typing comes from the
    # plan output schema — NOT from a code-side agent-slug → type map.
    artifact_type: str = "document"
    depends_on: list[int] = Field(default_factory=list)
    cost_estimate_tcredits: int = 0


class CoordinatorOutput(BaseModel):
    """Structured output schema enforced by Pydantic-AI Agent(result_type=...)."""

    summary: str
    delegation_plan: list[DelegationStep] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    confidence: str = "medium"  # 'high' | 'medium' | 'low'
    open_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    total_cost_credits: Decimal = Decimal(0)


# ── role-prompt + factory ────────────────────────────────────────────────


def get_role_prompt() -> RolePrompt:
    """Parse contracts/role-prompts/coordinator.md once per process."""
    return load_role_prompt(ROLE_KEY)


def build_coordinator_agent(
    *,
    model: LLMGatewayModel,
    role_prompt: RolePrompt | None = None,
) -> Agent[CoordinatorDeps, CoordinatorOutput]:
    """Construct the Coordinator Pydantic-AI Agent.

    Caller passes the model (real LLMGatewayModel wrapping LLMRouter, or
    FakeLLMGatewayModel for tests). The system prompt is loaded from
    contracts/role-prompts/coordinator.md unless overridden.
    """
    prompt = (role_prompt or get_role_prompt()).composed_system_prompt()
    return Agent(
        model=model,
        deps_type=CoordinatorDeps,
        # AC-W1-16b/24: plan-then-execute. The Coordinator emits the whole
        # delegation_plan as one PromptedOutput JSON completion (no function-
        # calling); runtime.dispatch.PlanExecutingCoordinator executes the plan
        # and re-applies the delegate_task depth/slug guards per step.
        output_type=PromptedOutput(CoordinatorOutput),
        system_prompt=prompt,
        tools=[],
    )


__all__ = [
    "ArtifactRef",
    "Citation",
    "CoordinatorDeps",
    "CoordinatorOutput",
    "DelegateInput",
    "DelegateResult",
    "DelegationStep",
    "ROLE_KEY",
    "build_coordinator_agent",
    "get_role_prompt",
]
