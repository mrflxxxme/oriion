"""Analyst — leaf specialist, structured analysis output.

Note: schema enum `role_category` is 'analyzer' (broader); UI slug + role-prompt
filename use 'analyst'. The seed in productivity_core_v1 maps slug=analyst →
role_category=analyzer to keep DB-side constraint + UX-side label in sync.

Wave 0: LLM-only (Pyodide capability lands Wave 2). Role-prompt explicitly
requires range estimates + capability-gap callouts for numerical claims.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.services.role_prompt_loader import RolePrompt, load_role_prompt
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

ROLE_KEY = "analyst"


class AnalystDeps(BaseModel):
    """Minimal deps."""


class AnalystOutput(BaseModel):
    """Free-form markdown body — Analyst emits sizing + matrix + positioning."""

    body_markdown: str


def get_role_prompt() -> RolePrompt:
    return load_role_prompt(ROLE_KEY)


def build_analyst_agent(
    *,
    model: LLMGatewayModel,
    role_prompt: RolePrompt | None = None,
) -> Agent[AnalystDeps, str]:
    # Wave-0 plain-text output (see researcher.py note — AC14/AC-W1-16).
    prompt = (role_prompt or get_role_prompt()).composed_system_prompt()
    return Agent(
        model=model,
        deps_type=AnalystDeps,
        output_type=str,
        system_prompt=prompt,
        tools=[],
    )


__all__ = ["ROLE_KEY", "AnalystDeps", "AnalystOutput", "build_analyst_agent"]
