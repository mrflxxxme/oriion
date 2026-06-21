"""Atomic cost-rollup: parent.cost = sum(direct steps + children.cost).

Per phase-spec AC6: parent.total_cost_credits == SUM(children.total_cost_credits +
direct task_steps.cost_credits). Walks the parent chain upward in one TX so
no intermediate state leaks.

⚠️ Cost-authority note (AC-W1-3, grill 2026-06-19 decision #7). The **live**
dispatch path does NOT use this utility — ``runtime.orchestrator`` sets
``task.total_cost_credits = ctx.accumulated_cost`` (the per-task **step-sum**,
which counts every billable LLM/delegation call exactly once and is the single
source of truth). This recursive ``steps + children`` rollup is a separate
reporting helper that is **only sound for trees where a task's delegation cost
lives in EITHER its own steps OR its children — not both**. Today
``runtime.dispatch.build_leaf_runner`` writes a delegation step on the parent
AND a lineage child Task with the same cost, so calling this on a *real
dispatched* task (horizontal or Master) would double-count. The Master path
(2-level, AC-W1-3.4) therefore reads ``task.total_cost_credits`` (orchestrator
authority) and never calls this. A unified rollup for genuine 3+ level trees is
deferred to Wave-2.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks.models import Task, TaskStep


async def rollup_task_cost(task_id: UUID, session: AsyncSession) -> Decimal:
    """Recompute total_cost_credits for task_id + all ancestors. Returns
    the final value for the root task."""
    current_id: UUID | None = task_id
    final_cost = Decimal(0)
    visited: set[UUID] = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        cost = await _compute_one(current_id, session)
        task = await session.get(Task, current_id)
        if task is None:
            break
        task.total_cost_credits = cost
        final_cost = cost
        current_id = task.parent_task_id
    await session.flush()
    return final_cost


async def _compute_one(task_id: UUID, session: AsyncSession) -> Decimal:
    """One task's cost = sum(direct task_steps) + sum(children.total_cost_credits)."""
    steps_stmt = select(TaskStep.cost_credits).where(TaskStep.task_id == task_id)
    step_costs = [row[0] for row in (await session.execute(steps_stmt)).all()]
    children_stmt = select(Task.total_cost_credits).where(Task.parent_task_id == task_id)
    child_costs = [row[0] for row in (await session.execute(children_stmt)).all()]
    return sum(step_costs, Decimal(0)) + sum(child_costs, Decimal(0))
