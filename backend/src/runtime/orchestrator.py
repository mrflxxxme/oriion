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

from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.observability.metrics import (
    TASK_DURATION,
    TASK_QUEUE_DEPTH,
    TASK_TOTAL,
)
from src.agents.tools.delegate import CoordinatorDepsLike, DelegateInput, DelegateResult
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

LeafRunner = Callable[[DelegateInput, "OrchestratorContext"], Awaitable[DelegateResult]]
"""Signature an orchestrator's leaf-dispatch callable must follow."""

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

    deps = CoordinatorDepsLike(
        cell_id=cell_id,
        task_id=task_id,
        user_id=user_id,
        available_agent_slugs=available_agent_slugs,
        current_depth=0,
        max_delegation_depth=5,
        runner=runner_with_orchestration,
    )

    # F-ARC-M2 audit fix: wrap Agent.run() in a try/except so any uncaught
    # exception (budget exceeded, provider failure, tool-call error) emits
    # task.failed via SSE — subscribers exit cleanly instead of hanging,
    # and reserved budget is refunded before propagation.
    try:
        # Pydantic-AI returns an AgentRunResult with .output (or .data,
        # depending on version) — defensive access keeps the bridge
        # version-tolerant.
        # coordinator_agent is typed Agent[CoordinatorDeps, CoordinatorOutput]
        # in agents/coordinator.py; here we pass the structurally-compatible
        # CoordinatorDepsLike shim (the runner-injection seam — see
        # agents/tools/delegate.py). Wave-1 AC-W1-7 collapses the two via
        # NullTeamProvisioningService.
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
        outcome = (
            "budget_exceeded" if str(error_code) == "llm_gateway.budget_exceeded" else "failed"
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

    # Cost rollup + completion stamp.
    completed_at = datetime.now(UTC)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    if task is not None:
        task.status = "succeeded"
        task.completed_at = completed_at
        task.total_cost_credits = ctx.accumulated_cost
        # F-CR-M1 audit fix: per-leaf result already encodes tokens_used as
        # a single total; honest accounting is to sum them on output_tokens
        # (matches provider-side convention where the completion is the
        # downstream-billable side) and leave input_tokens as zero at
        # Wave-0 granularity. Per-step persistence with proper split lands
        # Wave-1 alongside the Pydantic-AI per-step instrumentation hook.
        task.total_input_tokens = 0
        task.total_output_tokens = sum(r.tokens_used for r in ctx.leaf_outputs)
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
