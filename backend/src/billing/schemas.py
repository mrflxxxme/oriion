"""Pydantic response schemas for the billing API.

Money/credit fields are serialized as strings (decimal-as-string) — the same
convention as the SSE ledger — to avoid float-precision drift on the wire.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreditRateResponse(BaseModel):
    rub_per_credit: str
    fx_rate_usd_to_rub: str
    role_multiplier: str
    wave: str


class PlanResponse(BaseModel):
    slug: str
    name: str
    price_rub: str | None
    included_credits: str
    cells_limit: int | None
    agents_limit: int | None
    soft_cap_credits: str | None
    hard_cap_credits: str | None
    per_day_cap_credits: str | None
    trial_days: int | None
    byok_allowed: bool


class SubscriptionResponse(BaseModel):
    plan_slug: str
    status: str
    period_start: datetime
    period_end: datetime
    trial_ends_at: datetime | None
    credits_granted_this_period: str


class BalanceResponse(BaseModel):
    cell_id: UUID
    balance_credits: str
    period_usage_credits: str
    period_start: datetime | None
    period_end: datetime | None
    soft_cap_credits: str | None
    hard_cap_credits: str | None
    daily_usage_credits: str
    per_day_cap_credits: str | None


class TransactionResponse(BaseModel):
    id: UUID
    transaction_type: str
    amount_credits: str
    amount_rub: str
    balance_after_credits: str
    provider: str | None
    model: str | None
    task_id: UUID | None
    created_at: datetime
