"""Researcher — leaf specialist, web_search + read_url tools.

Phase 00.5b Commit 5 / AC-W1-19 / AC-W1-18. The Researcher can search the web
via a **native** Pydantic-AI tool: when DeepSeek is the active provider (it
forwards tool-calls — ADR-035), ``runtime.dispatch`` builds the agent with a
``web_search`` callable and the model autonomously decides when/what to search.
On YandexGPT/GigaChat failover (no tool forwarding) the agent is built tool-less
and the runtime falls back to the scripted ``fetch_research_context`` pre-fetch.

AC-W1-18: on the same DeepSeek path the Researcher also gets a ``read_url`` tool
so it can deep-read a promising source page (rate-limited, content-capped) after
a search — beyond snippets — within the AC10 cost cap.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.services.role_prompt_loader import RolePrompt, load_role_prompt
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

ROLE_KEY = "researcher"

NativeTool = Callable[[str], Awaitable[str]]
"""Native Researcher tool signature: ``async def tool(arg: str) -> str``.

The concrete callables (``web_search`` / ``read_url``) are built in
``runtime.dispatch`` (bound to the rate-limited MCP tools + Researcher
``agent_id``). Each callable's name, docstring and ``str`` parameter become the
Pydantic-AI ``ToolDefinition`` forwarded to the provider.
"""

# Backwards-compatible alias — ``web_search``'s historical type name.
WebSearchTool = NativeTool


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
    web_search: NativeTool | None = None,
    read_url: NativeTool | None = None,
) -> Agent[ResearcherDeps, str]:
    # Wave-0: plain-text output. The structured ResearcherOutput requires the
    # LLMGatewayModel structured-output / tool-call bridge (AC14/AC-W1-16) which
    # isn't wired yet — declaring it makes Pydantic-AI try to coerce free text
    # into the schema and fail (UnexpectedModelBehavior). The leaf produces
    # markdown; the demo/runtime consume it as text. ResearcherOutput is kept
    # for the Wave-1 structured path.
    #
    # AC-W1-19 / AC-W1-18: ``web_search`` + ``read_url`` (when supplied) are
    # registered as native tools so the model decides when/what to search and
    # which source to deep-read. They are only passed on the DeepSeek path
    # (ADR-035 gating in runtime.dispatch); on failover they stay None and the
    # runtime pre-fetches search context instead.
    prompt = (role_prompt or get_role_prompt()).composed_system_prompt()
    tools: list[NativeTool] = []
    if web_search is not None:
        tools.append(web_search)
    if read_url is not None:
        tools.append(read_url)
    return Agent(
        model=model,
        deps_type=ResearcherDeps,
        output_type=str,
        system_prompt=prompt,
        tools=tools,
    )


__all__ = [
    "ROLE_KEY",
    "NativeTool",
    "ResearcherDeps",
    "ResearcherOutput",
    "WebSearchTool",
    "build_researcher_agent",
]
