"""Aggregate credit caps — per-cell hard-cap + per-day kill-switch (R-04).

Admission gate: evaluated once at task start (the per-task 50/100 cap already
bounds a single admitted task, so per-cell overshoot is <= one task's cost).
Mid-task per-step per-cell enforcement is deferred (Wave-1 focused scope).

No-op when the cell has no active subscription (cells created outside the
register flow — tests, fixtures): without a plan there is nothing to enforce,
so existing task paths are unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.exceptions import CellQuotaExceeded, DailyQuotaExceeded
from src.billing.repositories import PlanRepository, SubscriptionRepository
from src.billing.services.balance_service import get_daily_usage, get_period_usage

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    """Outcome of an admission check (when not blocked by an exception)."""

    enforced: bool
    soft_warn: bool = False
    period_usage: Decimal = Decimal(0)
    soft_cap: Decimal | None = None
    hard_cap: Decimal | None = None
    daily_usage: Decimal = Decimal(0)
    per_day_cap: Decimal | None = None


async def enforce_quota_admission(session: AsyncSession, cell_id: UUID) -> QuotaStatus:
    """Block (raise) if the cell's period hard-cap or daily kill-switch is hit.

    Returns a ``QuotaStatus`` with ``soft_warn=True`` when the period soft-cap is
    reached (caller emits a non-blocking warning). No-op (``enforced=False``)
    when the cell has no active subscription/plan.
    """
    subscription = await SubscriptionRepository(session).get_active_by_cell(cell_id)
    if subscription is None:
        return QuotaStatus(enforced=False)
    plan = await PlanRepository(session).get(subscription.plan_slug)
    if plan is None:
        return QuotaStatus(enforced=False)

    period_usage = await get_period_usage(session, cell_id, period_start=subscription.period_start)
    daily_usage = await get_daily_usage(session, cell_id)

    # Per-day kill-switch first (R-04): catches a runaway loop even while the
    # monthly cap still has headroom.
    if plan.per_day_cap_credits is not None and daily_usage >= plan.per_day_cap_credits:
        logger.warning(
            "billing.quota.daily_block",
            cell_id=str(cell_id),
            daily_usage=str(daily_usage),
            per_day_cap=str(plan.per_day_cap_credits),
        )
        raise DailyQuotaExceeded(
            f"cell {cell_id} daily usage {daily_usage} >= per-day cap "
            f"{plan.per_day_cap_credits}"
        )

    if plan.hard_cap_credits is not None and period_usage >= plan.hard_cap_credits:
        logger.warning(
            "billing.quota.cell_block",
            cell_id=str(cell_id),
            period_usage=str(period_usage),
            hard_cap=str(plan.hard_cap_credits),
        )
        raise CellQuotaExceeded(
            f"cell {cell_id} period usage {period_usage} >= hard cap " f"{plan.hard_cap_credits}"
        )

    soft_warn = bool(plan.soft_cap_credits is not None and period_usage >= plan.soft_cap_credits)
    return QuotaStatus(
        enforced=True,
        soft_warn=soft_warn,
        period_usage=period_usage,
        soft_cap=plan.soft_cap_credits,
        hard_cap=plan.hard_cap_credits,
        daily_usage=daily_usage,
        per_day_cap=plan.per_day_cap_credits,
    )
