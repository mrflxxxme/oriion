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
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import select

from src.agents.analyst import AnalystDeps, build_analyst_agent
from src.agents.coordinator import (
    ArtifactRef,
    CoordinatorDeps,
    CoordinatorOutput,
    DelegationStep,
    build_coordinator_agent,
)
from src.agents.exceptions import RolePromptParseError
from src.agents.master import (
    ROLE_KEY_PLAN,
    ROLE_KEY_SYNTHESIS,
    MasterCallBilling,
    MasterDeps,
    MasterPlan,
    MasterResponse,
    build_master_plan_agent,
    build_master_synthesis_agent,
)
from src.agents.memory_curator import MemoryCallBilling
from src.agents.models import AgentArchetype
from src.agents.researcher import ResearcherDeps, build_researcher_agent
from src.agents.services.role_prompt_loader import load_master_prompt
from src.agents.strategic_context import StrategicContext
from src.agents.tools.delegate import (
    DEFAULT_MAX_DELEGATION_DEPTH,
    DelegateInput,
    DelegateResult,
    assert_delegation_allowed,
)
from src.agents.writer import WriterDeps, build_writer_agent
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel
from src.llm_gateway.services.billing_service import record_llm_cost
from src.mcp.tools.read_url import ReadURLTool
from src.mcp.tools.web_search import WebSearchTool
from src.multitenancy.models import Cell
from src.runtime.artifact_text import normalize_artifact_markdown, strip_wrapping_fence
from src.runtime.orchestrator import (
    MasterStepRecorder,
    MemoryExtractionHook,
    OrchestratorContext,
    QuotaAdmissionCheck,
    estimate_step_cost,
    execute_agent_task,
)
from src.runtime.sse_publisher import SSEPublisher, get_sse_publisher
from src.runtime.web_search_runner import (
    WEB_SEARCH_MAX_RESULTS,
    _default_web_search_tool,
    build_native_read_url,
    build_native_web_search,
    fetch_research_context,
)
from src.tasks.models import Task, TaskStep

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


# ── per-delegation billing + step persistence (AC-W1-2 / AC-W1-13) ─────────


@dataclass(frozen=True)
class StepBilling:
    """Everything the step recorder needs to bill + persist one delegation."""

    parent_task_id: UUID
    cell_id: UUID
    user_id: UUID
    step_index: int
    target_agent_slug: str
    provider_slug: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


# A recorder bills one delegation and returns its cost in credits. Injectable so
# unit tests substitute a fake (the production default writes real ledger + step
# rows, which need a real PG session).
StepRecorder = Callable[["AsyncSession", StepBilling], Awaitable[Decimal]]


async def _resolve_workspace_id(session: AsyncSession, cell_id: UUID) -> UUID:
    cell = await session.get(Cell, cell_id)
    if cell is None:
        raise LookupError(f"cell {cell_id} not found — cannot resolve workspace for billing")
    return cell.workspace_id


async def _resolve_archetype_id(
    session: AsyncSession, slug: str, *, vertical_slug: str | None = None
) -> UUID:
    """Resolve the active ``agent_archetypes`` row for a slug.

    ``task_steps.agent_archetype_id`` is a NOT-NULL FK, so a step can only be
    persisted once the archetype catalog is seeded. AC-W1-3 closes the former
    multi-vertical TODO: when ``vertical_slug`` is given the active row for THAT
    vertical wins (the Master archetype lives under its vertical); without it the
    newest active row for the slug is used (horizontal leaves, unambiguous since
    the marketing preset reuses the horizontal specialist archetypes).
    """
    stmt = select(AgentArchetype.id).where(
        AgentArchetype.slug == slug, AgentArchetype.is_active.is_(True)
    )
    if vertical_slug is not None:
        stmt = stmt.where(AgentArchetype.vertical_slug == vertical_slug)
    stmt = stmt.order_by(AgentArchetype.created_at.desc()).limit(1)
    archetype_id = (await session.execute(stmt)).scalars().first()
    if archetype_id is None:
        raise LookupError(
            f"no active agent_archetype for slug={slug!r} " f"(vertical_slug={vertical_slug!r})"
        )
    return archetype_id


async def record_delegation_step(session: AsyncSession, billing: StepBilling) -> Decimal:
    """Production step recorder (AC-W1-2 + AC-W1-13).

    1. Bill the call through the REAL ledger: ``record_llm_cost`` writes
       ``llm_usage_log`` + ``credit_transactions`` priced by the V4
       ``pricing_service`` (replaces the Wave-0 ``estimate_credits``). 1 credit =
       1 RUB, which equals the demo's 0.01-USD credit at the default FX=100, so
       the AC10 cost number is unchanged while becoming real per-provider.
    2. Persist a ``task_steps`` row on the PARENT task with the token split + the
       real cost. The orchestrator sums step costs into ``task.total_cost_credits``
       (never via the children, so there is no double count with the lineage
       child Task), giving ``task.total_* == sum(steps)``.

    Returns the step cost in credits (== ``cost_rub``).
    """
    workspace_id = await _resolve_workspace_id(session, billing.cell_id)
    request_id = uuid4().hex
    _cost_usd, cost_rub = await record_llm_cost(
        session,
        workspace_id=workspace_id,
        cell_id=billing.cell_id,
        user_id=billing.user_id,
        task_id=billing.parent_task_id,
        provider=billing.provider_slug,
        model=billing.model_name,
        tokens_in=billing.input_tokens,
        tokens_out=billing.output_tokens,
        latency_ms=billing.latency_ms,
        status="success",
        request_id=request_id,
    )
    archetype_id = await _resolve_archetype_id(session, billing.target_agent_slug)
    now = datetime.now(UTC)
    step = TaskStep(
        task_id=billing.parent_task_id,
        step_index=billing.step_index,
        agent_archetype_id=archetype_id,
        step_type="delegation",
        input_jsonb={"target_agent_slug": billing.target_agent_slug},
        output_jsonb={
            "input_tokens": billing.input_tokens,
            "output_tokens": billing.output_tokens,
            "provider": billing.provider_slug,
            "model": billing.model_name,
            "request_id": request_id,
        },
        status="succeeded",
        cost_credits=cost_rub,
    )
    step.started_at = now
    step.completed_at = now
    session.add(step)
    await session.flush()
    return cost_rub


async def record_master_call_step(session: AsyncSession, billing: MasterCallBilling) -> Decimal:
    """Bill + persist one Master-Agent LLM call (plan/synthesis) — AC-W1-3.

    Parallels ``record_delegation_step`` for the Master's OWN calls: bills via the
    real ledger (``record_llm_cost``) and writes a ``task_steps`` row
    (``step_type='llm_call'``) on the Master (parent) task, so the per-task
    step-sum (the cost authority, AC-W1-3.4) includes the +1-2 Master calls that
    R-32 flags (+15-20% tokens/vertical task). The archetype FK resolves to the
    vertical's Master archetype.
    """
    workspace_id = await _resolve_workspace_id(session, billing.cell_id)
    request_id = uuid4().hex
    _cost_usd, cost_rub = await record_llm_cost(
        session,
        workspace_id=workspace_id,
        cell_id=billing.cell_id,
        user_id=billing.user_id,
        task_id=billing.parent_task_id,
        provider=billing.provider_slug,
        model=billing.model_name,
        tokens_in=billing.input_tokens,
        tokens_out=billing.output_tokens,
        latency_ms=billing.latency_ms,
        status="success",
        request_id=request_id,
    )
    archetype_id = await _resolve_archetype_id(
        session, "master", vertical_slug=billing.vertical_tag
    )
    now = datetime.now(UTC)
    step = TaskStep(
        task_id=billing.parent_task_id,
        step_index=billing.step_index,
        agent_archetype_id=archetype_id,
        step_type="llm_call",
        input_jsonb={"phase": billing.phase},
        output_jsonb={
            "input_tokens": billing.input_tokens,
            "output_tokens": billing.output_tokens,
            "provider": billing.provider_slug,
            "model": billing.model_name,
            "request_id": request_id,
        },
        status="succeeded",
        cost_credits=cost_rub,
    )
    step.started_at = now
    step.completed_at = now
    session.add(step)
    await session.flush()
    return cost_rub


async def record_memory_call_step(session: AsyncSession, billing: MemoryCallBilling) -> Decimal:
    """Bill + persist one memory-curator LLM call (filter / summary) — 01.4b.

    Parallels ``record_master_call_step`` for the curator's own call: writes a
    ``task_steps`` row (``step_type='llm_call'`` — the step CHECK has no
    'memory_extraction' value, so the phase lives in ``input_jsonb`` instead)
    under the seeded ``memory_curator`` archetype, so the per-task step-sum (the
    cost authority) includes the auto-extraction overhead.

    The archetype + workspace are resolved BEFORE the ledger write so a missing
    ``memory_curator`` seed raises cleanly (the orchestrator runs this
    best-effort + swallows — this ordering avoids an orphan ledger debit).
    """
    workspace_id = await _resolve_workspace_id(session, billing.cell_id)
    archetype_id = await _resolve_archetype_id(session, "memory_curator")
    request_id = uuid4().hex
    _cost_usd, cost_rub = await record_llm_cost(
        session,
        workspace_id=workspace_id,
        cell_id=billing.cell_id,
        user_id=billing.user_id,
        task_id=billing.parent_task_id,
        provider=billing.provider_slug,
        model=billing.model_name,
        tokens_in=billing.input_tokens,
        tokens_out=billing.output_tokens,
        latency_ms=billing.latency_ms,
        status="success",
        request_id=request_id,
    )
    now = datetime.now(UTC)
    step = TaskStep(
        task_id=billing.parent_task_id,
        step_index=billing.step_index,
        agent_archetype_id=archetype_id,
        step_type="llm_call",
        input_jsonb={"phase": billing.phase, "kind": "memory_extraction"},
        output_jsonb={
            "input_tokens": billing.input_tokens,
            "output_tokens": billing.output_tokens,
            "provider": billing.provider_slug,
            "model": billing.model_name,
            "request_id": request_id,
        },
        status="succeeded",
        cost_credits=cost_rub,
    )
    step.started_at = now
    step.completed_at = now
    session.add(step)
    await session.flush()
    return cost_rub


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
    # Pydantic-AI is migrating ``.usage`` from a method to a property (a live
    # golden surfaced the deprecation warning). Handle BOTH so a version bump
    # doesn't silently zero the token counts (billing-token correctness).
    usage_attr = getattr(run_result, "usage", None)
    usage = usage_attr() if callable(usage_attr) else usage_attr
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
    step_recorder: StepRecorder | None = None,
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
        4. Bills the call + persists a ``task_steps`` row on the parent via
           ``step_recorder`` (AC-W1-2 / AC-W1-13) — defaults to the real-ledger
           ``record_delegation_step``; unit tests inject a no-DB fake.
        5. Persists a child ``Task`` row (status='succeeded') for lineage.
        6. Returns a ``DelegateResult`` with the real cost + token split.
    """
    specs = leaf_specs or _DEFAULT_LEAF_SPECS
    recorder = step_recorder or record_delegation_step
    step_index = 0

    async def _run_leaf(inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        nonlocal step_index
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
        call_start = perf_counter()
        run_result = await agent.run(sub_prompt, deps=spec.deps_factory())
        latency_ms = int((perf_counter() - call_start) * 1000)

        # Fence-stripping only: prior_context chaining must keep the role-
        # contract meta (frontmatter, structured summary) for downstream agents.
        output_text = strip_wrapping_fence(_extract_output_text(run_result))
        input_tokens, output_tokens = _extract_usage(run_result)

        # AC-W1-13: bill via the real ledger + persist a task_steps row. Provider/
        # model come from the model adapter's last failover selection.
        step_index += 1
        cost = await recorder(
            session,
            StepBilling(
                parent_task_id=parent_task_id,
                cell_id=cell_id,
                user_id=user_id,
                step_index=step_index,
                target_agent_slug=inp.target_agent_slug,
                provider_slug=getattr(model, "_last_provider_slug", None) or "",
                model_name=getattr(model, "_last_model_name", None) or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            ),
        )

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
            input_tokens=input_tokens,
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
        # AC-W1-3: propagate the strategic brief + depth fields so a Master's
        # subordinate Coordinator runs with the right context (and the depth
        # guards re-apply correctly). Defaults preserve the horizontal path.
        strategic_context = getattr(deps, "strategic_context", None)
        inner_deps = CoordinatorDeps(
            cell_id=deps.cell_id,
            task_id=deps.task_id,
            user_id=deps.user_id,
            available_agent_slugs=list(deps.available_agent_slugs),
            current_depth=int(getattr(deps, "current_depth", 0)),
            max_delegation_depth=int(
                getattr(deps, "max_delegation_depth", DEFAULT_MAX_DELEGATION_DEPTH)
            ),
            strategic_context=strategic_context,
        )
        # AC-W1-3.2: when a Master supplied a strategic brief, prepend it to the
        # Coordinator's prompt so the operational plan honours the domain
        # framing. ``None`` → prompt unchanged → horizontal byte-identical (3.1).
        effective_prompt = user_prompt
        if strategic_context is not None:
            effective_prompt = f"{strategic_context.as_coordinator_preamble()}\n\n{user_prompt}"
        plan_run = await agent.run(effective_prompt, deps=inner_deps)
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


# ── Master-Agent layer (ADR-029, AC-W1-3) ────────────────────────────────


@dataclass
class _MasterRunResult:
    """Mirror of AgentRunResult.output access used by the orchestrator."""

    output: MasterResponse


def _compose_master_synthesis_prompt(
    user_prompt: str, strategic_context: StrategicContext, coordinator_output: CoordinatorOutput
) -> str:
    """Build the Master's synthesis prompt from the team's operational output."""
    artifacts_block = (
        "\n\n".join(f"### {a.type}\n{a.path_or_inline}" for a in coordinator_output.artifacts)
        or coordinator_output.summary
    )
    return (
        "Ты — Master-Agent вертикали и доменный эксперт. Команда под управлением "
        "Координатора подготовила материалы ниже. Синтезируй финальный deliverable "
        "для пользователя: сведи материалы в один связный документ, проверь доменное "
        "качество, убери противоречия и дубли. Не выдумывай фактов и цифр.\n\n"
        f"## Запрос пользователя\n{user_prompt}\n\n"
        f"## Стратегическая цель\n{strategic_context.objective}\n\n"
        f"## Материалы команды\n{artifacts_block}"
    )


def _master_quality_check(final_artifact: str) -> tuple[bool, list[str]]:
    """Wave-1 soft domain-quality check — a flag, not a retry loop (Wave-2)."""
    notes: list[str] = []
    if not final_artifact.strip():
        notes.append("Master synthesis produced an empty deliverable.")
    return (not notes, notes)


class MasterAgent:
    """Wave-1 vertical Master-Agent (ADR-029): CEO above the Coordinator COO.

    Structurally compatible with the orchestrator's ``coordinator_agent`` slot
    (only ``.run(prompt, deps=...).output`` is consumed). For a vertical task:
      1. plan agent (deepseek-chat) → ``MasterPlan`` (domain interpretation),
         billed as an ``llm_call`` step via ``deps.master_recorder``;
      2. assemble a ``StrategicContext`` + delegate to the inner
         ``PlanExecutingCoordinator`` reusing ``deps.runner`` (leaf delegations
         bill + chain under the Master task exactly as horizontal);
      3. synthesis agent (deepseek-reasoner) → final deliverable, billed;
      4. return a ``MasterResponse`` (domain-quality flag is a soft Wave-1
         signal; the retry loop is Wave-2).

    Tests inject ``plan_agent`` / ``synthesis_agent`` / ``coordinator``
    (FakeLLMGatewayModel-backed); production builds them from ``llm_router``.
    """

    def __init__(
        self,
        *,
        vertical_tag: str,
        llm_router: LLMRouter | None = None,
        workspace_id: UUID | None = None,
        master_prompt: Any = None,
        plan_agent: Any = None,
        synthesis_agent: Any = None,
        coordinator: PlanExecutingCoordinator | None = None,
    ) -> None:
        self._vertical_tag = vertical_tag
        self._llm_router = llm_router
        self._workspace_id = workspace_id
        self._master_prompt = master_prompt
        self._plan_agent = plan_agent
        self._synthesis_agent = synthesis_agent
        self._coordinator = coordinator

    def _ensure_agents(self) -> tuple[Any, Any, Any, Any]:
        if self._plan_agent is not None and self._synthesis_agent is not None:
            return (
                self._plan_agent,
                getattr(self._plan_agent, "model", None),
                self._synthesis_agent,
                getattr(self._synthesis_agent, "model", None),
            )
        if self._llm_router is None or self._master_prompt is None:
            raise ValueError("MasterAgent needs (llm_router + master_prompt) or injected agents.")
        plan_model = LLMGatewayModel(
            role_key=ROLE_KEY_PLAN, llm_router=self._llm_router, workspace_id=self._workspace_id
        )
        synth_model = LLMGatewayModel(
            role_key=ROLE_KEY_SYNTHESIS,
            llm_router=self._llm_router,
            workspace_id=self._workspace_id,
        )
        return (
            build_master_plan_agent(model=plan_model, master_prompt=self._master_prompt),
            plan_model,
            build_master_synthesis_agent(model=synth_model, master_prompt=self._master_prompt),
            synth_model,
        )

    def _coordinator_for(self) -> PlanExecutingCoordinator:
        return self._coordinator or PlanExecutingCoordinator(
            llm_router=self._llm_router, workspace_id=self._workspace_id
        )

    async def run(self, user_prompt: str, *, deps: Any) -> _MasterRunResult:
        plan_agent, plan_model, synth_agent, synth_model = self._ensure_agents()
        master_deps = MasterDeps(
            cell_id=deps.cell_id,
            task_id=deps.task_id,
            user_id=deps.user_id,
            vertical_tag=self._vertical_tag,
        )

        # AC-W1-3: pre-call budget gate (symmetric with leaf delegations) — a
        # Master call that would breach the per-task cap is rejected BEFORE the
        # paid LLM call, so the aggregate cap is hard for the Master too.
        precheck = getattr(deps, "budget_precheck", None)

        # 1. Strategic plan (domain lens) — billed as the parent task's step 0.
        if precheck is not None:
            precheck(estimate_step_cost(ROLE_KEY_PLAN))
        t0 = perf_counter()
        plan_run = await plan_agent.run(user_prompt, deps=master_deps)
        plan_latency = int((perf_counter() - t0) * 1000)
        plan = getattr(plan_run, "output", None)
        if plan is None:
            plan = getattr(plan_run, "data", None)
        if not isinstance(plan, MasterPlan):
            raise TypeError(
                f"Master plan agent did not return a MasterPlan (got {type(plan).__name__})."
            )
        await self._bill(
            deps,
            model=plan_model,
            run_result=plan_run,
            phase="plan",
            step_index=0,
            latency_ms=plan_latency,
        )

        # 2. Delegate the operational objective to the subordinate Coordinator.
        strategic_context = StrategicContext(
            objective=plan.objective,
            vertical_tag=self._vertical_tag,
            domain_constraints=plan.domain_constraints,
            success_criteria=plan.success_criteria,
            parent_task_id=deps.task_id,
        )
        inner_deps = CoordinatorDeps(
            cell_id=deps.cell_id,
            task_id=deps.task_id,
            user_id=deps.user_id,
            available_agent_slugs=list(deps.available_agent_slugs),
            current_depth=int(getattr(deps, "current_depth", 0)),
            max_delegation_depth=int(
                getattr(deps, "max_delegation_depth", DEFAULT_MAX_DELEGATION_DEPTH)
            ),
            runner=deps.runner,
            strategic_context=strategic_context,
        )
        coord_run = await self._coordinator_for().run(strategic_context.objective, deps=inner_deps)
        coordinator_output = coord_run.output

        # 3. Domain-quality synthesis (free-text, R1) — billed after the leaves.
        # Pre-check here matters most: leaf costs have accumulated, so an
        # over-cap synthesis is rejected before the paid call (no over-cap bill).
        if precheck is not None:
            precheck(estimate_step_cost(ROLE_KEY_SYNTHESIS))
        synthesis_prompt = _compose_master_synthesis_prompt(
            user_prompt, strategic_context, coordinator_output
        )
        t1 = perf_counter()
        synth_run = await synth_agent.run(synthesis_prompt, deps=master_deps)
        synth_latency = int((perf_counter() - t1) * 1000)
        final_artifact = strip_wrapping_fence(_extract_output_text(synth_run)).strip()
        # Master steps use a collision-free index space vs the leaf delegation
        # steps (which occupy 1..len(artifacts)): plan=0, synthesis=len+1.
        synthesis_index = len(coordinator_output.artifacts) + 1
        await self._bill(
            deps,
            model=synth_model,
            run_result=synth_run,
            phase="synthesis",
            step_index=synthesis_index,
            latency_ms=synth_latency,
        )

        # 4. Soft domain-quality check (Wave-1: flag only; retry loop → Wave-2).
        passed, notes = _master_quality_check(final_artifact)
        return _MasterRunResult(
            output=MasterResponse(
                summary=coordinator_output.summary,
                final_artifact_markdown=final_artifact,
                domain_quality_passed=passed,
                domain_quality_notes=notes,
                coordinator_output=coordinator_output,
                confidence=coordinator_output.confidence,
            )
        )

    async def _bill(
        self,
        deps: Any,
        *,
        model: Any,
        run_result: Any,
        phase: str,
        step_index: int,
        latency_ms: int,
    ) -> None:
        """Bill one Master LLM call through the ctx-aware ``deps.master_recorder``."""
        recorder = getattr(deps, "master_recorder", None)
        if recorder is None:
            return
        in_tok, out_tok = _extract_usage(run_result)
        await recorder(
            MasterCallBilling(
                parent_task_id=deps.task_id,
                cell_id=deps.cell_id,
                user_id=deps.user_id,
                vertical_tag=self._vertical_tag,
                phase=phase,
                step_index=step_index,
                provider_slug=getattr(model, "_last_provider_slug", None) or "",
                model_name=getattr(model, "_last_model_name", None) or "",
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=latency_ms,
            )
        )


def resolve_master(
    vertical: str | None,
    *,
    llm_router: LLMRouter,
    workspace_id: UUID | None = None,
) -> MasterAgent | None:
    """Build the Master-Agent for ``vertical`` if a master-prompt exists, else None.

    A vertical without a ``masters/<vertical>.md`` prompt (or the horizontal
    ``None``) runs single-layer — the dispatcher falls back to the plain
    ``PlanExecutingCoordinator``.
    """
    if not vertical:
        return None
    try:
        master_prompt = load_master_prompt(vertical)
    except RolePromptParseError:
        return None
    return MasterAgent(
        vertical_tag=vertical,
        llm_router=llm_router,
        workspace_id=workspace_id,
        master_prompt=master_prompt,
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
    step_recorder: StepRecorder | None = None,
    quota_admission: QuotaAdmissionCheck | None = None,
    memory_extraction: MemoryExtractionHook | None = None,
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
    # AC-W1-3: a vertical cell (vertical_template_slug set + a master-prompt
    # present) routes through a Master-Agent (CEO → Coordinator COO); horizontal
    # cells keep the single-layer Coordinator. A caller-injected ``coordinator``
    # (unit tests) overrides detection. ``master_step_recorder`` is wired only on
    # the Master path so the orchestrator bills the Master's own LLM calls.
    master_step_recorder: MasterStepRecorder | None = None
    coord: Any
    if coordinator is not None:
        coord = coordinator
    else:
        cell = await session.get(Cell, task.cell_id)
        vertical = getattr(cell, "vertical_template_slug", None) if cell is not None else None
        master = resolve_master(vertical, llm_router=llm_router)
        if master is not None:
            coord = master
            master_step_recorder = record_master_call_step
        else:
            coord = PlanExecutingCoordinator(llm_router=llm_router)

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
        step_recorder=step_recorder,
    )

    return await execute_agent_task(
        task_id=task.id,
        cell_id=task.cell_id,
        user_id=task.initiated_by_user_id,
        # PlanExecutingCoordinator / MasterAgent are structurally compatible (.run);
        # ``coord`` is typed Any after vertical detection so no cast is needed.
        coordinator_agent=coord,
        user_prompt=user_prompt,
        available_agent_slugs=slugs,
        leaf_runner=leaf_runner,
        sse_publisher=publisher,
        session=session,
        master_step_recorder=master_step_recorder,
        quota_admission=quota_admission,
        memory_extraction=memory_extraction,
    )


__all__ = [
    "CREDIT_PER_INPUT_TOKEN",
    "CREDIT_PER_OUTPUT_TOKEN",
    "WEB_SEARCH_MAX_RESULTS",
    "MasterAgent",
    "PlanExecutingCoordinator",
    "StepBilling",
    "StepRecorder",
    "build_leaf_runner",
    "build_native_web_search",
    "dispatch_task",
    "estimate_credits",
    "fetch_research_context",
    "normalize_artifact_markdown",
    "record_delegation_step",
    "record_master_call_step",
    "record_memory_call_step",
    "resolve_master",
    "strip_wrapping_fence",
]
