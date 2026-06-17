"""Inline orchestrator-dispatch — closes the Phase 00.5b POST /tasks gap.

CRITICAL FINDING (Phase 00.6 PR-A live smoke): ``POST /tasks`` created a
``queued`` row but nothing ever invoked the orchestrator — the SSE stream
(`/tasks/{id}/stream`) waited forever because no events were ever published.

Phase 00.6 PR-B closes this with **Path #1 inline-dispatch**: a new endpoint
``POST /api/v1/cells/{cell_id}/tasks/{task_id}/run`` calls
``dispatch_task`` synchronously within the request (workers=1 invariant per
F-ARC-H2). This module is the wiring layer between the FastAPI handler and
the already-tested ``runtime.orchestrator.execute_agent_task``.

────────────────────────────────────────────────────────────────────────────
Plan-then-execute Coordinator (AC-W1-16b / AC-W1-24)
────────────────────────────────────────────────────────────────────────────
``PlanExecutingCoordinator`` runs the REAL LLM-driven Coordinator: it calls
``build_coordinator_agent`` (Pydantic-AI ``PromptedOutput``) to get a whole
``delegation_plan`` as one JSON completion — handling arbitrary user prompts,
not only the market-brief demo — then executes each plan step through
``deps.runner`` (the orchestrator's SSE + cost-rollup wrapper), re-applying the
``delegate_task`` depth/slug guards per step. Sub-prompts and artifact types
come from the plan, not from code-side framing: AC-W1-24 removed the Wave-0
``_SUB_PROMPT_FRAMING`` / ``DEFAULT_PIPELINE`` / ``_ARTIFACT_KIND`` constants.

``PromptedOutput`` is plain text in/out, so this needs NO tool-forwarding in
``LLMGatewayModel`` (native tool-calls = AC-W1-19, a later pin). Each specialist
is still a real LLM call (through ``LLMGatewayModel`` + ``LLMRouter`` failover),
so the demo produces real artifacts, latency (AC8), and cost (AC10).

**Still deferred (AC-W1-16a):** dispatch stays inline-synchronous; the swap to
a Dramatiq actor (return 202 immediately) + Redis-pubsub SSE (AC-W1-1) is the
infra-PR follow-up.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.agents.analyst import AnalystDeps, build_analyst_agent
from src.agents.coordinator import (
    ArtifactRef,
    CoordinatorDeps,
    CoordinatorOutput,
    DelegationStep,
    build_coordinator_agent,
)
from src.agents.researcher import ResearcherDeps, build_researcher_agent
from src.agents.tools.delegate import (
    DelegateInput,
    DelegateResult,
    assert_delegation_allowed,
)
from src.agents.writer import WriterDeps, build_writer_agent
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel
from src.mcp.tools.read_url import ReadURLTool
from src.mcp.tools.web_search import WebSearchTool
from src.runtime.artifact_text import normalize_artifact_markdown, strip_wrapping_fence
from src.runtime.orchestrator import OrchestratorContext, execute_agent_task
from src.runtime.sse_publisher import SSEPublisher, get_sse_publisher
from src.runtime.web_search_runner import (
    WEB_SEARCH_MAX_RESULTS,
    _default_web_search_tool,
    build_native_read_url,
    build_native_web_search,
    fetch_research_context,
)
from src.tasks.models import Task

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.llm_gateway.services.router_service import LLMRouter
    from src.mcp.tools.rate_limit import ToolRateLimiter

# ── Wave-0 cost estimate ──────────────────────────────────────────────────
# A T-credit ≈ 0.01 USD per ADR-018. DeepSeek-chat list price (2026) is
# ≈ $0.27 / 1M input + $1.10 / 1M output tokens. Converted to T-credits:
#   input :  0.27 USD / 1M tok / 0.01 USD-per-credit = 0.000027 credit/tok
#   output:  1.10 USD / 1M tok / 0.01 USD-per-credit = 0.000110 credit/tok
# This keeps AC10 (cost cap <= 0.30 USD == 30 credits) meaningful for the
# 10x staging demo. AC-W1-13 replaces this estimate with real per-callsite
# cost from ``billing_service.record_llm_cost`` (which reads the live
# provider price table + FX rate).
CREDIT_PER_INPUT_TOKEN = Decimal("0.000027")
CREDIT_PER_OUTPUT_TOKEN = Decimal("0.000110")

# Per-specialist builder + deps-class map. Injectable so unit tests can
# substitute fakes that don't construct a real Pydantic-AI Agent.
LeafAgentFactory = Callable[..., Any]


@dataclass(frozen=True)
class _LeafSpec:
    build: LeafAgentFactory
    deps_factory: Callable[[], Any]


_DEFAULT_LEAF_SPECS: dict[str, _LeafSpec] = {
    "researcher": _LeafSpec(build_researcher_agent, ResearcherDeps),
    "analyst": _LeafSpec(build_analyst_agent, AnalystDeps),
    "writer": _LeafSpec(build_writer_agent, WriterDeps),
}


def estimate_credits(*, input_tokens: int, output_tokens: int) -> Decimal:
    """Wave-0 coarse cost estimate (AC-W1-13 swaps for real billing)."""
    return (
        Decimal(input_tokens) * CREDIT_PER_INPUT_TOKEN
        + Decimal(output_tokens) * CREDIT_PER_OUTPUT_TOKEN
    )


def _extract_output_text(run_result: Any) -> str:
    """Pull the markdown body off a Pydantic-AI AgentRunResult, version-tolerant."""
    output = getattr(run_result, "output", None)
    if output is None:
        output = getattr(run_result, "data", None)
    if output is None:
        return ""
    body = getattr(output, "body_markdown", None)
    if isinstance(body, str):
        return body
    return str(output)


def _extract_usage(run_result: Any) -> tuple[int, int]:
    """Return ``(input_tokens, output_tokens)`` from an AgentRunResult.

    Pydantic-AI versions vary: ``.usage()`` may expose
    ``input_tokens``/``output_tokens`` (newer) or
    ``request_tokens``/``response_tokens`` (older). Defensive across both.
    """
    usage_fn = getattr(run_result, "usage", None)
    usage = usage_fn() if callable(usage_fn) else None
    if usage is None:
        return 0, 0
    input_tokens = (
        getattr(usage, "input_tokens", None) or getattr(usage, "request_tokens", None) or 0
    )
    output_tokens = (
        getattr(usage, "output_tokens", None) or getattr(usage, "response_tokens", None) or 0
    )
    return int(input_tokens), int(output_tokens)


def build_leaf_runner(
    *,
    llm_router: LLMRouter,
    session: AsyncSession,
    parent_task_id: UUID,
    cell_id: UUID,
    user_id: UUID,
    workspace_id: UUID | None = None,
    leaf_specs: dict[str, _LeafSpec] | None = None,
    web_search_tool: WebSearchTool | None = None,
    native_web_search: Callable[[str], Awaitable[str]] | None = None,
    native_read_url: Callable[[str], Awaitable[str]] | None = None,
    user_prompt: str = "",
) -> Callable[[DelegateInput, OrchestratorContext], Awaitable[DelegateResult]]:
    """Build the production leaf-dispatch callable.

    For each delegation the runner:
        1. (Researcher only) wires web_search. On the DeepSeek path
           (``native_web_search`` supplied — ADR-035) the tool is registered on
           the agent and the model searches autonomously (AC-W1-19); otherwise the
           runner pre-fetches live web_search context and prepends it to the
           sub-prompt (scripted failover path).
        2. Builds the target specialist Agent (real ``LLMGatewayModel``).
        3. Runs it against the (possibly research-augmented) sub_prompt.
        4. Persists a child ``Task`` row (status='succeeded').
        5. Returns a ``DelegateResult`` with estimated cost + token usage.
    """
    specs = leaf_specs or _DEFAULT_LEAF_SPECS

    async def _run_leaf(inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        spec = specs.get(inp.target_agent_slug)
        if spec is None:
            raise KeyError(
                f"no leaf spec for slug={inp.target_agent_slug!r}; " f"known={sorted(specs)}"
            )

        model = LLMGatewayModel(
            role_key=inp.target_agent_slug,
            llm_router=llm_router,
            workspace_id=workspace_id,
        )

        sub_prompt = inp.sub_prompt
        build_kwargs: dict[str, Any] = {"model": model}
        if inp.target_agent_slug == "researcher":
            if native_web_search is not None:
                # DeepSeek path: the model owns the search loop (no pre-fetch).
                build_kwargs["web_search"] = native_web_search
                # AC-W1-18: pair read_url with web_search on the native path so
                # the model can deep-read a source beyond snippets.
                if native_read_url is not None:
                    build_kwargs["read_url"] = native_read_url
            elif web_search_tool is not None:
                # Failover path: prepend scripted live context (founder 2026-06-07).
                context = await fetch_research_context(
                    web_search_tool, user_prompt or inp.sub_prompt
                )
                if context:
                    sub_prompt = f"{context}\n\n{inp.sub_prompt}"

        agent = spec.build(**build_kwargs)
        run_result = await agent.run(sub_prompt, deps=spec.deps_factory())

        # Fence-stripping only: prior_context chaining must keep the role-
        # contract meta (frontmatter, structured summary) for downstream agents.
        output_text = strip_wrapping_fence(_extract_output_text(run_result))
        input_tokens, output_tokens = _extract_usage(run_result)
        cost = estimate_credits(input_tokens=input_tokens, output_tokens=output_tokens)

        now = datetime.now(UTC)
        child = Task(
            cell_id=cell_id,
            initiated_by_user_id=user_id,
            parent_task_id=parent_task_id,
            title=f"{inp.target_agent_slug} sub-task",
            description=inp.sub_prompt[:255],
            input_jsonb={"prompt": inp.sub_prompt},
            status="succeeded",
        )
        child.started_at = now
        child.completed_at = now
        child.total_cost_credits = cost
        child.total_input_tokens = input_tokens
        child.total_output_tokens = output_tokens
        session.add(child)
        await session.flush()  # materialize child.id

        return DelegateResult(
            sub_task_id=child.id,
            target_agent_slug=inp.target_agent_slug,
            output=output_text,
            cost_credits=cost,
            tokens_used=output_tokens,
        )

    return _run_leaf


@dataclass
class _PlanRunResult:
    """Mirror of Pydantic-AI's AgentRunResult.output access used by the orchestrator."""

    output: CoordinatorOutput


def _ordered_steps(steps: list[DelegationStep]) -> list[DelegationStep]:
    """Stable topological order honouring ``depends_on`` (by step number).

    The market-brief demo plan is linear (1→2→3); arbitrary plans may declare a
    dependency out of input order. ``visited`` is marked before recursing, so a
    malformed cyclic plan can't loop forever — it degrades to input order.
    """
    by_num = {s.step: s for s in steps}
    visited: set[int] = set()
    order: list[DelegationStep] = []

    def _visit(s: DelegationStep) -> None:
        if s.step in visited:
            return
        visited.add(s.step)
        for dep in s.depends_on:
            dep_step = by_num.get(dep)
            if dep_step is not None:
                _visit(dep_step)
        order.append(s)

    for s in steps:
        _visit(s)
    return order


def _compose_sub_prompt(goal: str, prior_context: str) -> str:
    """Sub-prompt = the Coordinator's self-sufficient step goal + chained context.

    No code-side role framing (AC-W1-24): the ``goal`` carries the instruction
    the Coordinator itself wrote; ``prior_context`` chains the upstream
    specialists' (un-normalized) output so e.g. the analyst sees the research.
    """
    if prior_context:
        return f"{goal}\n\n{prior_context}"
    return goal


class PlanExecutingCoordinator:
    """Real LLM-driven Coordinator (AC-W1-16b / AC-W1-24), plan-then-execute.

    1. Run the Coordinator agent (``PromptedOutput``) → a full ``delegation_plan``.
    2. Execute each step in dependency order via ``deps.runner`` (the
       orchestrator's SSE + cost-rollup wrapper), re-applying the delegate_task
       depth/slug guards (the Coordinator no longer calls the tool itself).
    3. Materialize one artifact per executed step, typed from ``step.artifact_type``.

    The Coordinator agent is built from ``llm_router`` in production; tests inject
    a pre-built ``coordinator_agent`` backed by ``FakeLLMGatewayModel``.
    """

    def __init__(
        self,
        *,
        llm_router: LLMRouter | None = None,
        workspace_id: UUID | None = None,
        coordinator_agent: Any = None,
    ) -> None:
        self._llm_router = llm_router
        self._workspace_id = workspace_id
        self._coordinator_agent = coordinator_agent

    def _build_agent(self) -> Any:
        if self._coordinator_agent is not None:
            return self._coordinator_agent
        if self._llm_router is None:
            raise ValueError("PlanExecutingCoordinator needs an llm_router or a coordinator_agent.")
        model = LLMGatewayModel(
            role_key="coordinator",
            llm_router=self._llm_router,
            workspace_id=self._workspace_id,
        )
        return build_coordinator_agent(model=model)

    async def run(self, user_prompt: str, *, deps: Any) -> _PlanRunResult:
        agent = self._build_agent()
        inner_deps = CoordinatorDeps(
            cell_id=deps.cell_id,
            task_id=deps.task_id,
            user_id=deps.user_id,
            available_agent_slugs=list(deps.available_agent_slugs),
        )
        plan_run = await agent.run(user_prompt, deps=inner_deps)
        plan = getattr(plan_run, "output", None)
        if plan is None:
            plan = getattr(plan_run, "data", None)
        if not isinstance(plan, CoordinatorOutput):
            raise TypeError(
                "Coordinator agent did not return a CoordinatorOutput "
                f"(got {type(plan).__name__})."
            )

        available = list(deps.available_agent_slugs)
        current_depth = int(getattr(deps, "current_depth", 0))
        max_depth = int(getattr(deps, "max_delegation_depth", 5))
        artifacts: list[ArtifactRef] = []
        prior_context = ""
        for step in _ordered_steps(plan.delegation_plan):
            # The Coordinator no longer calls delegate_task as a tool, so we
            # re-apply its in-team + depth guards here (AC-W1-16b).
            assert_delegation_allowed(
                step.agent,
                available=available,
                current_depth=current_depth,
                max_depth=max_depth,
            )
            sub_prompt = _compose_sub_prompt(step.goal, prior_context)
            result = await deps.runner(
                DelegateInput(target_agent_slug=step.agent, sub_prompt=sub_prompt),
                deps,
            )
            step.status = "completed"
            # prior_context keeps the un-normalized meta for downstream agents;
            # the user-facing artifact below is fully normalized.
            prior_context = (
                f"{prior_context}\n\n## {step.agent} output\n{result.output}"
                if prior_context
                else f"## {step.agent} output\n{result.output}"
            )
            artifacts.append(
                ArtifactRef(
                    id=str(result.sub_task_id),
                    type=step.artifact_type,
                    path_or_inline=normalize_artifact_markdown(result.output),
                )
            )

        return _PlanRunResult(
            output=CoordinatorOutput(
                summary=plan.summary,
                delegation_plan=plan.delegation_plan,
                citations=plan.citations,
                artifacts=artifacts,
                confidence=plan.confidence,
                open_questions=plan.open_questions,
                assumptions=plan.assumptions,
            )
        )


def _router_supports_native_tools(llm_router: Any, role_key: str) -> bool:
    """Defensively ask the router whether ``role_key`` would run on a tool-capable
    provider (DeepSeek). Returns False for routers without the predicate (e.g. the
    ``object()`` stand-in used by no-delegation unit tests)."""
    predicate = getattr(llm_router, "would_use_native_tools", None)
    return bool(predicate(role_key)) if callable(predicate) else False


async def dispatch_task(
    *,
    task: Task,
    session: AsyncSession,
    llm_router: LLMRouter,
    sse_publisher: SSEPublisher | None = None,
    available_agent_slugs: list[str] | None = None,
    coordinator: PlanExecutingCoordinator | None = None,
    web_search_tool: WebSearchTool | None = None,
    tool_rate_limiter: ToolRateLimiter | None = None,
) -> dict[str, Any]:
    """Synchronously run the orchestrator for a queued task.

    Returns the structured CoordinatorOutput dict (the orchestrator also
    emits the SSE ledger to ``sse_publisher`` so ``/stream`` subscribers see
    the full event log via drain-replay).

    Researcher web_search wiring is DeepSeek-gated (ADR-035): when DeepSeek is the
    active provider the Researcher gets a **native** ``web_search`` tool (rate-
    limited via ``tool_rate_limiter``) and decides its own searches (AC-W1-19); on
    YandexGPT/GigaChat failover it falls back to the scripted pre-fetch.
    """
    publisher = sse_publisher or get_sse_publisher()
    slugs = available_agent_slugs or list(_DEFAULT_LEAF_SPECS)
    coord = coordinator or PlanExecutingCoordinator(llm_router=llm_router)

    # DeepSeek active → native tool-call path (rate-limited); else scripted.
    native_enabled = _router_supports_native_tools(llm_router, "researcher")
    search_tool = web_search_tool or _default_web_search_tool(
        rate_limiter=tool_rate_limiter if native_enabled else None
    )
    native_web_search = build_native_web_search(search_tool) if native_enabled else None
    # AC-W1-18: deep-read tool, DeepSeek-gated like web_search. ReadURLTool
    # requires a rate limiter (10/min, SSRF-guarded), so it's wired only when one
    # is supplied; without it the Researcher keeps web_search-only behaviour.
    native_read_url = (
        build_native_read_url(ReadURLTool(tool_rate_limiter))
        if native_enabled and tool_rate_limiter is not None
        else None
    )

    user_prompt = ""
    if isinstance(task.input_jsonb, dict):
        user_prompt = str(task.input_jsonb.get("prompt", ""))

    leaf_runner = build_leaf_runner(
        llm_router=llm_router,
        session=session,
        parent_task_id=task.id,
        cell_id=task.cell_id,
        user_id=task.initiated_by_user_id,
        web_search_tool=search_tool,
        native_web_search=native_web_search,
        native_read_url=native_read_url,
        user_prompt=user_prompt,
    )

    return await execute_agent_task(
        task_id=task.id,
        cell_id=task.cell_id,
        user_id=task.initiated_by_user_id,
        coordinator_agent=coord,  # type: ignore[arg-type]  # PlanExecutingCoordinator is structurally compatible (.run)
        user_prompt=user_prompt,
        available_agent_slugs=slugs,
        leaf_runner=leaf_runner,
        sse_publisher=publisher,
        session=session,
    )


__all__ = [
    "CREDIT_PER_INPUT_TOKEN",
    "CREDIT_PER_OUTPUT_TOKEN",
    "WEB_SEARCH_MAX_RESULTS",
    "PlanExecutingCoordinator",
    "build_leaf_runner",
    "build_native_web_search",
    "dispatch_task",
    "estimate_credits",
    "fetch_research_context",
    "normalize_artifact_markdown",
    "strip_wrapping_fence",
]
