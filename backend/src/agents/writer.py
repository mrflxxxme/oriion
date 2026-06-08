"""Writer — leaf specialist, markdown / content-plan / tone-of-voice output."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.services.role_prompt_loader import RolePrompt, load_role_prompt
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

ROLE_KEY = "writer"


class WriterDeps(BaseModel):
    """Minimal deps."""


class WriterOutput(BaseModel):
    """Free-form markdown body — Writer emits brief + content-plan."""

    body_markdown: str


def get_role_prompt() -> RolePrompt:
    return load_role_prompt(ROLE_KEY)


def build_writer_agent(
    *,
    model: LLMGatewayModel,
    role_prompt: RolePrompt | None = None,
) -> Agent[WriterDeps, str]:
    # Wave-0 plain-text output (see researcher.py note — AC14/AC-W1-16).
    prompt = (role_prompt or get_role_prompt()).composed_system_prompt()
    return Agent(
        model=model,
        deps_type=WriterDeps,
        output_type=str,
        system_prompt=prompt,
        tools=[],
    )


__all__ = ["ROLE_KEY", "WriterDeps", "WriterOutput", "build_writer_agent"]
