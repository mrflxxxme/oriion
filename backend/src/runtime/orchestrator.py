"""Orchestrator — drives Pydantic-AI Agent.run() with task-step persistence.

Phase 00.5b Commit 6 (minimum viable). Wave 0 happy path:
    1. Reserve budget (50 T-credit cap).
    2. Emit task.started SSE.
    3. Run the supplied Agent against the user prompt + Coordinator deps.
    4. For each delegate_task call, persist a task_step row (delegation),
       and the corresponding child Task / steps for the leaf specialist.
    5. After Agent.run() returns, roll up cost into parent.total_cost_credits,
       persist the final CoordinatorOutput, and emit task.completed.

Full task_step persistence per LLM token + SSE token streaming lands in
Wave 1+ (requires hooking Pydantic-AI's per-step instrumentation, deferred
to Phase 01.x retro). For Wave 0 the demo flow integration test (Commit 7)
asserts the coarser event order via the in-process SSEPublisher.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.observability.metrics import (
    TASK_DURATION,
    TASK_QUEUE_DEPTH,
    TASK_TOTAL,
)
from src.agents.master import MasterCallBilling
from src.agents.tools.delegate import CoordinatorDeps, DelegateInput, DelegateResult
from src.billing.services.quota_service import QuotaStatus
from src.llm_gateway.services.router_service import resolve_max_tokens
from src.runtime.budget_guard import (
    DEFAULT_TASK_CAP_TCREDITS,
    check_budget,
    refund_unused,
    reserve,
)
from src.runtime.sse_events import TaskStreamEvent
from src.runtime.sse_publisher import SSEPublisher
from src.tasks import events as tasks_events
from src.tasks.exceptions import TaskCancelled
from src.tasks.models import Task

logger = structlog.get_logger(__name__)

LeafRunner = Callable[[DelegateInput, "OrchestratorContext"], Awaitable[DelegateResult]]
"""Signature an orchestrator's leaf-dispatch callable must follow."""

# AC-W1-3: session-bound biller for a Master's own LLM call (plan / synthesis).
# Built by ``runtime.dispatch`` (it has the session); the orchestrator wraps it
# into the ctx-aware ``CoordinatorDeps.master_recorder`` (budget + SSE).
MasterStepRecorder = Callable[[AsyncSession, MasterCallBilling], Awaitable[Decimal]]

# AC-01.3.5/.6: injected per-cell + per-day quota admission check. Optional seam
# (default None ⇒ no-op) so the orchestrator's unit tests run against fake
# sessions without a billing DB; the worker (runtime.queue.actor) wires the real
# ``billing.services.quota_service.enforce_quota_admission``.
QuotaAdmissionCheck = Callable[[AsyncSession, UUID], Awaitable[QuotaStatus]]

# AC-01.4.7: injected post-task memory auto-extraction hook (01.4b). Optional seam
# (default None ⇒ no-op) so the orchestrator's unit tests run without an LLM; the
# worker wires the real filter-agent via
# ``runtime.memory_extraction.build_memory_extraction_hook``. Args: (final
# deliverable text, collision-free step_index); returns (billed_cost, input_tokens,
# output_tokens) — the cost folds into the per-task cap + step-sum, the tokens roll
# into the task token totals (so cost + tokens stay consistent, like the Master).
MemoryExtractionHook = Callable[[str, int], Awaitable[tuple[Decimal, int, int]]]

# P1-D forward-estimate constants. Mirror runtime.dispatch.estimate_credits's
# DeepSeek per-token T-credit rates (kept local to avoid the dispatch→
# orchestrator import cycle). The PRE-call check is intentionally conservative:
# it bills the step's full output budget (resolve_max_tokens) so an over-budget
# step is rejected before the paid LLM call.
_CREDIT_PER_OUTPUT_TOKEN = Decimal("0.000110")


def estimate_step_cost(target_agent_slug: str) -> Decimal:
    """Conservative forward cost estimate for one delegation step.

    Prices the step at its full per-role output-token budget so the pre-call
    ``check_budget`` rejects a step that *would* blow the cap before it runs
    (e.g. the writer's max_tokens=8192). Real per-callsite cost is reconciled
    afterward via ``accumulated_cost`` (AC-W1-13 swaps both for live billing).
    """
    return Decimal(resolve_max_tokens(target_agent_slug)) * _CREDIT_PER_OUTPUT_TOKEN


async def _read_persisted_status(session: AsyncSession, task: Task | None) -> str | None:
    """Re-read the task's status from the DB so a concurrently-committed
    ``cancel_task`` (P1-C) is visible mid-run.

    ``cancel_task`` commits ``status='cancelled'`` on a *different* session; with
    ``expire_on_commit=False`` the orchestrator's identity-mapped row is stale,
    so we ``refresh`` (re-SELECT) before reading. Returns None when there is no
    row to refresh (purged-task race) or the session shim has no ``refresh``.
    """
    if task is None:
        return None
    refresh = getattr(session, "refresh", None)
    if callable(refresh):
        await refresh(task, attribute_names=["status"])
    return task.status


# The top-level task IS the Coordinator run; its duration is labelled accordingly
# (per-leaf durations are a Wave-1+ task_steps concern, see AC-W1-2).
_TASK_ROLE_KEY = "coordinator"


def _record_terminal_task_metrics(
    *, cell_label: str, outcome: str, started_at: datetime, completed_at: datetime
) -> None:
    """Observe task_duration_seconds + inc task_total + release the queue gauge.

    AC-W1-13: called once per task from each terminal branch (succeeded /
    failed / budget_exceeded). Pairs with the ``TASK_QUEUE_DEPTH.inc()`` at
    task-start so the gauge nets back. Process-global metrics, so this is the
    same exposition the worker's /metrics serves under async dispatch.
    """
    duration_seconds = (completed_at - started_at).total_seconds()
    TASK_DURATION.labels(role_key=_TASK_ROLE_KEY, outcome=outcome).observe(duration_seconds)
    TASK_TOTAL.labels(cell_id=cell_label, outcome=outcome).inc()
    TASK_QUEUE_DEPTH.labels(cell_id=cell_label).dec()


def _deliverable_text(output: Any) -> str:
    """Filter-agent input (grill Q7): the Master's synthesized deliverable if
    present, else the Coordinator summary, else a string fallback."""
    if output is None:
        return ""
    final = getattr(output, "final_artifact_markdown", None)
    if isinstance(final, str) and final.strip():
        return final
    summary = getattr(output, "summary", None)
    if isinstance(summary, str):
        return summary
    return str(output)


class OrchestratorContext:
    """Run-state shared across Coordinator → leaf delegations."""

    def __init__(
        self,
        *,
        task_id: UUID,
        cell_id: UUID,
        user_id: UUID,
        sse_publisher: SSEPublisher,
        budget_cap: Decimal = DEFAULT_TASK_CAP_TCREDITS,
    ) -> None:
        self.task_id = task_id
        self.cell_id = cell_id
        self.user_id = user_id
        self.sse_publisher = sse_publisher
        self.budget_cap = budget_cap
        self.accumulated_cost = Decimal(0)
        self.leaf_outputs: list[DelegateResult] = []
        # AC-W1-3: Master plan/synthesis token counts (their cost folds into
        # accumulated_cost; their tokens roll up here so task.total_*_tokens
        # reconciles with task.total_cost_credits on the Master path).
        self.master_input_tokens = 0
        self.master_output_tokens = 0
        # AC-01.4.7: the post-task memory-extraction call's tokens. Its cost folds
        # into accumulated_cost; its tokens roll up here so task.total_*_tokens
        # stays consistent with total_cost_credits (same contract as the Master).
        self.memory_input_tokens = 0
        self.memory_output_tokens = 0


async def execute_agent_task(
    *,
    task_id: UUID,
    cell_id: UUID,
    user_id: UUID,
    coordinator_agent: Agent,
    user_prompt: str,
    available_agent_slugs: list[str],
    leaf_runner: LeafRunner,
    sse_publisher: SSEPublisher,
    session: AsyncSession,
    budget_cap: Decimal = DEFAULT_TASK_CAP_TCREDITS,
    master_step_recorder: MasterStepRecorder | None = None,
    quota_admission: QuotaAdmissionCheck | None = None,
    memory_extraction: MemoryExtractionHook | None = None,
) -> dict[str, Any]:
    """Run the Coordinator agent end-to-end + emit SSE event ledger.

    Returns the structured CoordinatorOutput as a dict. The supplied
    ``leaf_runner`` is invoked from ``delegate_task`` when Coordinator
    decides to dispatch to a specialist — Commit 7 wires the production
    runner that materializes child Task rows; the demo-flow integration
    test passes a fake runner that returns canned DelegateResult.
    """
    ctx = OrchestratorContext(
        task_id=task_id,
        cell_id=cell_id,
        user_id=user_id,
        sse_publisher=sse_publisher,
        budget_cap=budget_cap,
    )
    reserved = reserve(budget_cap)
    started_at = datetime.now(UTC)

    await sse_publisher.publish(
        TaskStreamEvent(
            event_type="task.started",
            task_id=task_id,
            payload={"started_at": started_at.isoformat()},
        )
    )
    await tasks_events.emit_task_started(task_id=task_id, started_at=started_at)

    # AC-W1-13: a task enters the running pool — bump the per-cell gauge. The
    # matching decrement runs in BOTH terminal branches (success + failure) so
    # the gauge nets back to its pre-task level. Runs in the Dramatiq worker
    # process under async dispatch (ADR-034).
    cell_label = str(cell_id)
    TASK_QUEUE_DEPTH.labels(cell_id=cell_label).inc()

    # Flip task to running.
    task = await session.get(Task, task_id)
    if task is not None:
        task.status = "running"
        task.started_at = started_at

    # Bind a leaf-runner adapter into CoordinatorDeps so the Pydantic-AI
    # `delegate_task` tool can dispatch through us. Each dispatch pushes
    # accumulated cost + emits SSE delegation events.
    async def runner_with_orchestration(inp: DelegateInput, _deps: Any) -> DelegateResult:
        # P1-C fix: honour a mid-run cancel. cancel_task commits
        # status='cancelled' on another session; re-read the persisted status
        # before each delegation step and abort (no further paid steps) so the
        # cancel actually stops the orchestration instead of running to
        # completion. The TaskCancelled handler below stamps the terminal
        # 'cancelled' outcome (never overwritten to 'succeeded').
        if await _read_persisted_status(session, task) == "cancelled":
            raise TaskCancelled(f"task {task_id} cancelled mid-run")
        await sse_publisher.publish(
            TaskStreamEvent(
                event_type="task.delegation_started",
                task_id=task_id,
                payload={"target_agent_slug": inp.target_agent_slug},
            )
        )
        # P1-D fix: enforce the cap BEFORE the paid call by passing a forward
        # cost estimate as pending_cost. A single expensive step (e.g. the
        # writer at max_tokens=8192) is rejected up-front instead of running in
        # full and only tripping the AFTER-check (honours budget_guard's
        # pre-call contract — see check_budget docstring).
        check_budget(
            accumulated_cost=ctx.accumulated_cost,
            pending_cost=estimate_step_cost(inp.target_agent_slug),
            cap=ctx.budget_cap,
        )
        result = await leaf_runner(inp, ctx)
        ctx.accumulated_cost += result.cost_credits
        ctx.leaf_outputs.append(result)
        check_budget(accumulated_cost=ctx.accumulated_cost, cap=ctx.budget_cap)
        await sse_publisher.publish(
            TaskStreamEvent(
                event_type="task.delegation_completed",
                task_id=task_id,
                payload={
                    "target_agent_slug": inp.target_agent_slug,
                    "sub_task_id": str(result.sub_task_id),
                    "cost_credits": str(result.cost_credits),
                    "tokens_used": result.tokens_used,
                },
            )
        )
        return result

    # AC-W1-3: ctx-aware recorder for a Master's own LLM calls (plan/synthesis).
    # Symmetric to ``runner_with_orchestration`` for leaves — it bills via the
    # session-bound ``master_step_recorder`` then folds the cost into the SAME
    # ``ctx.accumulated_cost`` so the per-task 50-credit cap covers the whole
    # Master + children aggregate (R-32 / R-04). Master calls post-check the cap
    # (they are bounded at 2 per task; the unbounded leaf fan-out keeps the
    # pre-call check). Only wired when a Master path supplied a recorder.
    async def master_call_recorder(billing: MasterCallBilling) -> Decimal:
        cost = await master_step_recorder(session, billing)  # type: ignore[misc]
        ctx.accumulated_cost += cost
        # Roll the Master call's tokens up alongside its cost so the per-task
        # token totals reconcile with total_cost_credits (no leaf-only undercount).
        ctx.master_input_tokens += billing.input_tokens
        ctx.master_output_tokens += billing.output_tokens
        check_budget(accumulated_cost=ctx.accumulated_cost, cap=ctx.budget_cap)
        await sse_publisher.publish(
            TaskStreamEvent(
                event_type="task.step_completed",
                task_id=task_id,
                payload={"phase": billing.phase, "cost_credits": str(cost)},
            )
        )
        return cost

    # Pre-call budget gate for the Master's own LLM calls — symmetric with the
    # leaf pre-check (a Master call that *would* blow the cap is rejected BEFORE
    # the paid call, so the aggregate cap is hard for the Master too, not just
    # post-checked). The Master passes a forward estimate as pending_cost.
    def master_budget_precheck(pending_cost: Decimal) -> None:
        check_budget(
            accumulated_cost=ctx.accumulated_cost,
            pending_cost=pending_cost,
            cap=ctx.budget_cap,
        )

    deps = CoordinatorDeps(
        cell_id=cell_id,
        task_id=task_id,
        user_id=user_id,
        available_agent_slugs=available_agent_slugs,
        current_depth=0,
        max_delegation_depth=5,
        runner=runner_with_orchestration,
        master_recorder=master_call_recorder if master_step_recorder is not None else None,
        budget_precheck=master_budget_precheck if master_step_recorder is not None else None,
    )

    # F-ARC-M2 audit fix: wrap Agent.run() in a try/except so any uncaught
    # exception (budget exceeded, provider failure, tool-call error) emits
    # task.failed via SSE — subscribers exit cleanly instead of hanging,
    # and reserved budget is refunded before propagation.
    try:
        # AC-01.3.5/.6: per-cell + per-day quota admission gate. No-op when the
        # cell has no active subscription (cells created outside register —
        # tests/fixtures). Raises CellQuotaExceeded / DailyQuotaExceeded (caught
        # by the failure handler below → task.failed with the billing code) when
        # the aggregate cap is already exhausted. Soft-cap emits a non-blocking
        # warning. Note: admission-time only — a single admitted task can still
        # overshoot the per-cell cap by at most one per-task budget (50); mid-task
        # per-step per-cell enforcement is deferred (Wave-1 focused scope).
        # Injected seam: None in unit tests (no billing DB), real check in the worker.
        if quota_admission is not None:
            quota = await quota_admission(session, cell_id)
            if quota.soft_warn:
                await sse_publisher.publish(
                    TaskStreamEvent(
                        event_type="task.budget_warning",
                        task_id=task_id,
                        payload={
                            "reason": "cell_soft_cap",
                            "period_usage_credits": str(quota.period_usage),
                            "soft_cap_credits": str(quota.soft_cap),
                            "hard_cap_credits": str(quota.hard_cap),
                        },
                    )
                )

        # Pydantic-AI returns an AgentRunResult with .output (or .data,
        # depending on version) — defensive access keeps the bridge
        # version-tolerant.
        # coordinator_agent is typed Agent[CoordinatorDeps, CoordinatorOutput].
        # AC-W1-7: CoordinatorDeps is now the single deps type (the former
        # CoordinatorDepsLike shim is collapsed into it — see
        # agents/tools/delegate.py), with the runner-injection seam preserved.
        run_result = await coordinator_agent.run(user_prompt, deps=deps)  # type: ignore[call-overload]
        output = getattr(run_result, "output", None) or getattr(run_result, "data", None)
    except TaskCancelled:
        # P1-C fix: a mid-run cancel aborts the orchestration with a terminal
        # 'cancelled' outcome. Do NOT overwrite task.status — cancel_task
        # already committed 'cancelled'; the orchestrator only stamps
        # completion + emits the cancelled SSE/CloudEvent so subscribers exit
        # cleanly. Reserved budget is refunded; status is never resurrected to
        # 'succeeded' (the bug this fix closes).
        completed_at = datetime.now(UTC)
        if task is not None:
            task.completed_at = completed_at
            task.total_cost_credits = ctx.accumulated_cost
        refund_unused(ctx.accumulated_cost, reserved)
        _record_terminal_task_metrics(
            cell_label=cell_label,
            outcome="cancelled",
            started_at=started_at,
            completed_at=completed_at,
        )
        await sse_publisher.publish(
            TaskStreamEvent(
                event_type="task.cancelled",
                task_id=task_id,
                payload={"total_cost_credits": str(ctx.accumulated_cost)},
            )
        )
        await tasks_events.emit_task_cancelled(task_id=task_id, cascaded_to=[])
        return {"summary": "(cancelled)", "total_cost_credits": str(ctx.accumulated_cost)}
    except Exception as exc:
        completed_at = datetime.now(UTC)
        if task is not None:
            task.status = "failed"
            task.completed_at = completed_at
            task.total_cost_credits = ctx.accumulated_cost
        refund_unused(ctx.accumulated_cost, reserved)
        error_code = getattr(exc, "code", exc.__class__.__name__)
        # The runtime budget guard raises tasks.exceptions.BudgetExceeded
        # (code='tasks.budget_exceeded') — including for the Master aggregate cap.
        # (llm_gateway.budget_exceeded kept for the BYOK gateway-side variant.)
        # AC-01.3.5/.6: the billing aggregate quotas (per-cell hard-cap +
        # per-day kill-switch) share the budget_exceeded metric outcome; the
        # task.failed SSE carries the specific billing.* code for the client.
        outcome = (
            "budget_exceeded"
            if str(error_code)
            in (
                "tasks.budget_exceeded",
                "llm_gateway.budget_exceeded",
                "billing.cell_quota_exceeded",
                "billing.daily_quota_exceeded",
            )
            else "failed"
        )
        _record_terminal_task_metrics(
            cell_label=cell_label,
            outcome=outcome,
            started_at=started_at,
            completed_at=completed_at,
        )
        await sse_publisher.publish(
            TaskStreamEvent(
                event_type="task.failed",
                task_id=task_id,
                payload={
                    "error_code": str(error_code),
                    "error_message": str(exc),
                    "retry_possible": False,
                    "total_cost_credits": str(ctx.accumulated_cost),
                },
            )
        )
        await tasks_events.emit_task_failed(
            task_id=task_id,
            error_code=str(error_code),
            retry_possible=False,
        )
        raise

    # P1-C fix: re-read persisted status before the success write so a cancel
    # that landed during the final Coordinator turn (after the last delegation
    # step) is not clobbered. If the row is already terminal-cancelled, abort
    # the success write and emit the cancelled outcome instead of resurrecting
    # it to 'succeeded'.
    if await _read_persisted_status(session, task) == "cancelled":
        completed_at = datetime.now(UTC)
        if task is not None:
            task.completed_at = completed_at
            task.total_cost_credits = ctx.accumulated_cost
        refund_unused(ctx.accumulated_cost, reserved)
        _record_terminal_task_metrics(
            cell_label=cell_label,
            outcome="cancelled",
            started_at=started_at,
            completed_at=completed_at,
        )
        await sse_publisher.publish(
            TaskStreamEvent(
                event_type="task.cancelled",
                task_id=task_id,
                payload={"total_cost_credits": str(ctx.accumulated_cost)},
            )
        )
        await tasks_events.emit_task_cancelled(task_id=task_id, cascaded_to=[])
        return {"summary": "(cancelled)", "total_cost_credits": str(ctx.accumulated_cost)}

    # AC-01.4.7 memory auto-extraction (01.4b). SUCCESS path only (grill Q4): run
    # the injected filter-agent hook on the final deliverable BEFORE the cost
    # rollup, so its billed cost folds into accumulated_cost (→ total_cost_credits,
    # preserving total == SUM(steps)). The step index sits above the leaf (1..N) +
    # Master synthesis (N+1) indices → collision-free under the unique
    # (task_id, step_index) constraint. Best-effort: a housekeeping failure must
    # NEVER flip a succeeded task to failed (grill Q5 — never reject), so the whole
    # call is swallowed; cost folds only on a clean return (the extractor writes
    # the task_step LAST, so a clean return guarantees the step exists).
    if memory_extraction is not None:
        try:
            mem_cost, mem_in, mem_out = await memory_extraction(
                _deliverable_text(output), len(ctx.leaf_outputs) + 2
            )
            ctx.accumulated_cost += mem_cost
            ctx.memory_input_tokens += mem_in
            ctx.memory_output_tokens += mem_out
            await sse_publisher.publish(
                TaskStreamEvent(
                    event_type="task.step_completed",
                    task_id=task_id,
                    payload={"phase": "memory_extraction", "cost_credits": str(mem_cost)},
                )
            )
        except Exception as exc:  # housekeeping must never fail a succeeded task
            logger.warning(
                "runtime.memory_extraction.failed",
                task_id=str(task_id),
                error=str(exc),
            )

    # Cost rollup + completion stamp.
    completed_at = datetime.now(UTC)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    if task is not None:
        task.status = "succeeded"
        task.completed_at = completed_at
        # AC-W1-2: task totals roll up from the per-delegation steps. Each leaf
        # result carries the real cost + token split (the leaf runner persisted a
        # matching task_steps row), so task.total_* == sum(steps). Cost is summed
        # from the steps, never from the lineage child Tasks, so there is no
        # double count.
        task.total_cost_credits = ctx.accumulated_cost
        # AC-W1-3: token totals = leaf delegations + the Master's own plan/synthesis
        # calls, so they reconcile with total_cost_credits (cost includes both).
        task.total_input_tokens = (
            sum(r.input_tokens for r in ctx.leaf_outputs)
            + ctx.master_input_tokens
            + ctx.memory_input_tokens
        )
        task.total_output_tokens = (
            sum(r.tokens_used for r in ctx.leaf_outputs)
            + ctx.master_output_tokens
            + ctx.memory_output_tokens
        )
    refund_unused(ctx.accumulated_cost, reserved)
    _record_terminal_task_metrics(
        cell_label=cell_label,
        outcome="succeeded",
        started_at=started_at,
        completed_at=completed_at,
    )

    if output is None:
        output_dict: dict[str, Any] = {"summary": "(no output)"}
    elif hasattr(output, "model_dump"):
        output_dict = output.model_dump()
    else:
        output_dict = {"summary": str(output)}
    output_dict["total_cost_credits"] = str(ctx.accumulated_cost)

    await sse_publisher.publish(
        TaskStreamEvent(
            event_type="task.completed",
            task_id=task_id,
            payload={
                "result": output_dict,
                "total_cost_credits": str(ctx.accumulated_cost),
                "total_duration_ms": duration_ms,
            },
        )
    )
    await tasks_events.emit_task_completed(
        task_id=task_id,
        total_cost_credits=ctx.accumulated_cost,
        total_duration_ms=duration_ms,
        result_summary={"delegation_count": len(ctx.leaf_outputs)},
    )
    return output_dict
