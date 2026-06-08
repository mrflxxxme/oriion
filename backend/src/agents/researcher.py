"""Researcher — leaf specialist, web_search + read_url tools.

Phase 00.5b Commit 5. Real tool wiring lands when src.mcp.tools.{web_search,
read_url} stabilize their public callable shape (Wave 1+). For Wave 0 the
demo flow path runs against the canned FakeLLMGatewayModel — Researcher
returns shape-correct competitive matrix without hitting any external API.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.services.role_prompt_loader import RolePrompt, load_role_prompt
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

ROLE_KEY = "researcher"


class ResearcherDeps(BaseModel):
    """Minimal deps — Researcher is invoked by Coordinator via
    ctx.deps.runner, so per-run state lives in the runner closure."""


class ResearcherOutput(BaseModel):
    """Free-form markdown body — Researcher emits research-pack content."""

    body_markdown: str


def get_role_prompt() -> RolePrompt:
    return load_role_prompt(ROLE_KEY)


def build_researcher_agent(
    *,
    model: LLMGatewayModel,
    role_prompt: RolePrompt | None = None,
) -> Agent[ResearcherDeps, str]:
    # Wave-0: plain-text output. The structured ResearcherOutput requires the
    # LLMGatewayModel structured-output / tool-call bridge (AC14/AC-W1-16) which
    # isn't wired yet — declaring it makes Pydantic-AI try to coerce free text
    # into the schema and fail (UnexpectedModelBehavior). The leaf produces
    # markdown; the demo/runtime consume it as text. ResearcherOutput is kept
    # for the Wave-1 structured path.
    prompt = (role_prompt or get_role_prompt()).composed_system_prompt()
    return Agent(
        model=model,
        deps_type=ResearcherDeps,
        output_type=str,
        system_prompt=prompt,
        tools=[],  # web_search + read_url wire-up Wave 1
    )


__all__ = ["ROLE_KEY", "ResearcherDeps", "ResearcherOutput", "build_researcher_agent"]
