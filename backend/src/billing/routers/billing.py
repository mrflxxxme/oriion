"""Billing read API — credit-rate, plans, subscription, balance, transactions.

All money/credit values are emitted as decimal-strings (see schemas). Per-cell
endpoints are RLS-scoped via ``get_tenant_db_session`` + ``get_current_cell_id``;
``/credit-rate`` and ``/plans`` are global (auth required, no cell scope).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.session import get_db
from src._shared.middleware.tenant_context import (
    get_current_cell_id,
    get_tenant_db_session,
)
from src.billing.exceptions import SubscriptionNotFound
from src.billing.models import Plan, Subscription
from src.billing.repositories import PlanRepository, SubscriptionRepository
from src.billing.schemas import (
    BalanceResponse,
    CreditRateResponse,
    PlanResponse,
    SubscriptionResponse,
    TransactionResponse,
)
from src.billing.services import balance_service
from src.billing.services.credit_rate_service import get_credit_rate
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.rbac.deps import require_cell_permission
from src.rbac.permissions import BILLING_VIEW

router = APIRouter(prefix="/billing", tags=["billing"])


def _plan_to_response(plan: Plan) -> PlanResponse:
    return PlanResponse(
        slug=plan.slug,
        name=plan.name,
        price_rub=str(plan.price_rub) if plan.price_rub is not None else None,
        included_credits=str(plan.included_credits),
        cells_limit=plan.cells_limit,
        agents_limit=plan.agents_limit,
        soft_cap_credits=(
            str(plan.soft_cap_credits) if plan.soft_cap_credits is not None else None
        ),
        hard_cap_credits=(
            str(plan.hard_cap_credits) if plan.hard_cap_credits is not None else None
        ),
        per_day_cap_credits=(
            str(plan.per_day_cap_credits) if plan.per_day_cap_credits is not None else None
        ),
        trial_days=plan.trial_days,
        byok_allowed=plan.byok_allowed,
    )


def _subscription_to_response(sub: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        plan_slug=sub.plan_slug,
        status=sub.status,
        period_start=sub.period_start,
        period_end=sub.period_end,
        trial_ends_at=sub.trial_ends_at,
        credits_granted_this_period=str(sub.credits_granted_this_period),
    )


@router.get("/credit-rate", response_model=CreditRateResponse)
async def credit_rate(
    _auth: AuthenticatedUser = Depends(get_current_user),
) -> CreditRateResponse:
    rate = get_credit_rate()
    return CreditRateResponse(
        rub_per_credit=str(rate.rub_per_credit),
        fx_rate_usd_to_rub=str(rate.fx_rate_usd_to_rub),
        role_multiplier=str(rate.role_multiplier),
        wave=rate.wave,
    )


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    _auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlanResponse]:
    # Global catalog (no RLS) → raw session is sufficient.
    plans = await PlanRepository(db).list_active()
    return [_plan_to_response(p) for p in plans]


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_cell_permission(BILLING_VIEW))],
)
async def get_subscription(
    db: AsyncSession = Depends(get_tenant_db_session),
    cell_id: UUID = Depends(get_current_cell_id),
) -> SubscriptionResponse:
    sub = await SubscriptionRepository(db).get_active_by_cell(cell_id)
    if sub is None:
        raise SubscriptionNotFound("no active subscription for the current cell")
    return _subscription_to_response(sub)


@router.get(
    "/balance",
    response_model=BalanceResponse,
    dependencies=[Depends(require_cell_permission(BILLING_VIEW))],
)
async def get_balance(
    db: AsyncSession = Depends(get_tenant_db_session),
    cell_id: UUID = Depends(get_current_cell_id),
) -> BalanceResponse:
    sub = await SubscriptionRepository(db).get_active_by_cell(cell_id)
    balance = await balance_service.get_balance(db, cell_id)
    daily_usage = await balance_service.get_daily_usage(db, cell_id)

    period_usage = period_start = period_end = None
    soft_cap = hard_cap = per_day_cap = None
    if sub is not None:
        period_start = sub.period_start
        period_end = sub.period_end
        period_usage = await balance_service.get_period_usage(
            db, cell_id, period_start=sub.period_start
        )
        plan = await PlanRepository(db).get(sub.plan_slug)
        if plan is not None:
            soft_cap = plan.soft_cap_credits
            hard_cap = plan.hard_cap_credits
            per_day_cap = plan.per_day_cap_credits

    return BalanceResponse(
        cell_id=cell_id,
        balance_credits=str(balance),
        period_usage_credits=str(period_usage if period_usage is not None else 0),
        period_start=period_start,
        period_end=period_end,
        soft_cap_credits=str(soft_cap) if soft_cap is not None else None,
        hard_cap_credits=str(hard_cap) if hard_cap is not None else None,
        daily_usage_credits=str(daily_usage),
        per_day_cap_credits=str(per_day_cap) if per_day_cap is not None else None,
    )


@router.get(
    "/transactions",
    response_model=list[TransactionResponse],
    dependencies=[Depends(require_cell_permission(BILLING_VIEW))],
)
async def list_transactions(
    db: AsyncSession = Depends(get_tenant_db_session),
    cell_id: UUID = Depends(get_current_cell_id),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TransactionResponse]:
    rows = await balance_service.list_transactions(
        db, cell_id, date_from=date_from, date_to=date_to, limit=limit
    )
    return [
        TransactionResponse(
            id=row.id,
            transaction_type=row.transaction_type,
            amount_credits=str(row.amount_credits),
            amount_rub=str(row.amount_rub),
            balance_after_credits=str(row.balance_after_credits),
            provider=row.provider,
            model=row.model,
            task_id=row.task_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
