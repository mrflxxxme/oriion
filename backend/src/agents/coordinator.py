"""Coordinator — top-level orchestrator of the productivity-core preset.

Wave 0: horizontal preset, no Master-Agent layer above. Coordinator is
the single role with the ``delegate_task`` tool — leaf specialists
(Researcher, Writer, Analyst) cannot delegate (per ADR-016 team-first UX).

Per phase-spec 00.5 inline definition + ADR-022 (Coordinator top-level in
horizontal preset).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.agents.services.role_prompt_loader import RolePrompt, load_role_prompt
from src.agents.tools.delegate import (
    DelegateInput,
    DelegateResult,
    delegate_task,
)
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

ROLE_KEY = "coordinator"


# ── deps + output schema (structured Pydantic-AI output) ────────────────


class CoordinatorDeps(BaseModel):
    """Per-run dependency injection container."""

    model_config = {"arbitrary_types_allowed": True}

    cell_id: UUID
    task_id: UUID
    user_id: UUID
    available_agent_slugs: list[str] = Field(
        default_factory=lambda: ["researcher", "writer", "analyst"]
    )
    current_depth: int = 0
    max_delegation_depth: int = 5
    # in-process runner for demo-flow tests; runtime orchestrator (Commit 6)
    # injects the real DB-backed runner.
    runner: Any = None


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
        output_type=CoordinatorOutput,
        system_prompt=prompt,
        tools=[delegate_task],
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
