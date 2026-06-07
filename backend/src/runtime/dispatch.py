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
Wave-0 deterministic pipeline (NOT LLM-driven delegation)
────────────────────────────────────────────────────────────────────────────
The full LLM-driven Coordinator → ``delegate_task`` tool-call loop requires
``LLMGatewayModel.request()`` to forward tools + the structured-output schema
to the provider. Wave-0's adapter intentionally does NOT do that yet (see the
F-ARC-M1 note in ``llm_gateway/pydantic_ai_model.py`` + the demo-flow test
docstring — full tool-call path is AC14 Wave-1 hardening).

So for Wave-0 the dispatch uses a ``ScriptedCoordinator`` that drives a fixed
researcher → analyst → writer pipeline. Each specialist IS a real LLM call
(through ``LLMGatewayModel`` + ``LLMRouter`` failover chain), so the demo
produces real artifacts, real end-to-end latency (AC8), and real cost (AC10).
What's deterministic is only the *decomposition* — the Coordinator doesn't
decide the plan via an LLM tool-call, it always runs the canonical 3-step
brief pipeline.

**AC-W1-16** pins the swap of ``ScriptedCoordinator`` for the real
LLM-driven Coordinator (once the adapter forwards tools/output-schema) AND
the swap of inline-synchronous dispatch for a Dramatiq actor (so the request
returns 202 immediately instead of blocking for the whole orchestration).
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
    CoordinatorOutput,
)
from src.agents.researcher import ResearcherDeps, build_researcher_agent
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.agents.writer import WriterDeps, build_writer_agent
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel
from src.runtime.orchestrator import OrchestratorContext, execute_agent_task
from src.runtime.sse_publisher import SSEPublisher, get_sse_publisher
from src.tasks.models import Task

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.llm_gateway.services.router_service import LLMRouter

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

DEFAULT_PIPELINE: tuple[str, ...] = ("researcher", "analyst", "writer")

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
) -> Callable[[DelegateInput, OrchestratorContext], Awaitable[DelegateResult]]:
    """Build the production leaf-dispatch callable.

    For each delegation the runner:
        1. Builds the target specialist Agent (real ``LLMGatewayModel``).
        2. Runs it against ``inp.sub_prompt`` (one real LLM call).
        3. Persists a child ``Task`` row (status='succeeded').
        4. Returns a ``DelegateResult`` with estimated cost + token usage.
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
        agent = spec.build(model=model)
        run_result = await agent.run(inp.sub_prompt, deps=spec.deps_factory())

        output_text = _extract_output_text(run_result)
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


class ScriptedCoordinator:
    """Wave-0 deterministic stand-in for the LLM-driven Coordinator.

    Drives the canonical researcher → analyst → writer brief pipeline by
    calling ``deps.runner`` once per specialist (chaining each output into
    the next sub-prompt). Returns a ``CoordinatorOutput`` so the orchestrator
    serializes it identically to the real path.

    AC-W1-16: replace with the real LLM-driven Coordinator once
    ``LLMGatewayModel`` forwards tools + output-schema to the provider.
    """

    def __init__(self, *, pipeline: tuple[str, ...] = DEFAULT_PIPELINE) -> None:
        self._pipeline = pipeline

    async def run(self, user_prompt: str, *, deps: Any) -> _ScriptedRunResult:
        artifacts: list[ArtifactRef] = []
        prior_context = ""
        for slug in self._pipeline:
            sub_prompt = self._compose_sub_prompt(slug, user_prompt, prior_context)
            result = await deps.runner(
                DelegateInput(target_agent_slug=slug, sub_prompt=sub_prompt),
                deps,
            )
            prior_context = (
                f"{prior_context}\n\n## {slug} output\n{result.output}"
                if prior_context
                else f"## {slug} output\n{result.output}"
            )
            artifacts.append(
                ArtifactRef(
                    id=str(result.sub_task_id),
                    type=_ARTIFACT_KIND.get(slug, "analysis"),
                    path_or_inline=result.output,
                )
            )
        summary = (
            "Market & content brief produced via the Wave-0 deterministic "
            f"pipeline ({' → '.join(self._pipeline)})."
        )
        return _ScriptedRunResult(output=CoordinatorOutput(summary=summary, artifacts=artifacts))

    @staticmethod
    def _compose_sub_prompt(slug: str, user_prompt: str, prior_context: str) -> str:
        framing = _SUB_PROMPT_FRAMING.get(slug, "")
        if prior_context:
            return f"{framing}\n\nИсходный запрос:\n{user_prompt}\n\n{prior_context}"
        return f"{framing}\n\nИсходный запрос:\n{user_prompt}"


@dataclass
class _ScriptedRunResult:
    """Mirror of Pydantic-AI's AgentRunResult.output access used by the orchestrator."""

    output: CoordinatorOutput


_ARTIFACT_KIND: dict[str, str] = {
    "researcher": "matrix",
    "analyst": "analysis",
    "writer": "brief",
}

_SUB_PROMPT_FRAMING: dict[str, str] = {
    "researcher": (
        "Ты Researcher. Собери конкурентный анализ рынка и оформи "
        "конкурентную матрицу (≥5 строк × ≥4 колонки: Игрок | Сегмент | "
        "Сильная сторона | Слабая сторона) на основе запроса ниже."
    ),
    "analyst": (
        "Ты Analyst. На основе исследования рынка дай sizing, оценку "
        "сегментов и позиционные рекомендации (с диапазонами, без "
        "ложной точности)."
    ),
    "writer": (
        "Ты Writer. Подготовь market brief (≥1500 слов на русском) и "
        "контент-план ровно на 10 постов на основе исследования и анализа."
    ),
}


async def dispatch_task(
    *,
    task: Task,
    session: AsyncSession,
    llm_router: LLMRouter,
    sse_publisher: SSEPublisher | None = None,
    available_agent_slugs: list[str] | None = None,
    coordinator: ScriptedCoordinator | None = None,
) -> dict[str, Any]:
    """Synchronously run the orchestrator for a queued task.

    Returns the structured CoordinatorOutput dict (the orchestrator also
    emits the SSE ledger to ``sse_publisher`` so ``/stream`` subscribers see
    the full event log via drain-replay).
    """
    publisher = sse_publisher or get_sse_publisher()
    slugs = available_agent_slugs or list(DEFAULT_PIPELINE)
    coord = coordinator or ScriptedCoordinator()

    user_prompt = ""
    if isinstance(task.input_jsonb, dict):
        user_prompt = str(task.input_jsonb.get("prompt", ""))

    leaf_runner = build_leaf_runner(
        llm_router=llm_router,
        session=session,
        parent_task_id=task.id,
        cell_id=task.cell_id,
        user_id=task.initiated_by_user_id,
    )

    return await execute_agent_task(
        task_id=task.id,
        cell_id=task.cell_id,
        user_id=task.initiated_by_user_id,
        coordinator_agent=coord,  # type: ignore[arg-type]  # ScriptedCoordinator is structurally compatible (.run)
        user_prompt=user_prompt,
        available_agent_slugs=slugs,
        leaf_runner=leaf_runner,
        sse_publisher=publisher,
        session=session,
    )


__all__ = [
    "CREDIT_PER_INPUT_TOKEN",
    "CREDIT_PER_OUTPUT_TOKEN",
    "DEFAULT_PIPELINE",
    "ScriptedCoordinator",
    "build_leaf_runner",
    "dispatch_task",
    "estimate_credits",
]
