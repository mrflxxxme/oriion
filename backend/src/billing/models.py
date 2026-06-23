"""SQLAlchemy 2.x models for the billing bounded context.

- ``CreditTransaction`` — append-only credit ledger (Wave 0 skeleton).
- ``Plan`` — tariff catalog (Phase 01.3). Migration ``billing/0002_plans.py``.
- ``Subscription`` — cell↔plan binding (Phase 01.3).
  Migration ``billing/0003_subscriptions.py``.

Schema authoritative per the billing migrations + ADR-008-credits-billing.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base


class CreditTransaction(Base):
    """Append-only credit ledger row.

    Each LLM call writes ONE row of transaction_type='debit' atomically with
    one row of llm_gateway.llm_usage_log (same transaction, same session) per
    llm-gateway invariant #7.
    """

    __tablename__ = "credit_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('debit','credit','refund','trial_grant')",
            name="credit_transactions_type_check",
        ),
        Index("ix_credit_tx_cell_created", "cell_id", text("created_at DESC")),
        Index("ix_credit_tx_workspace_created", "workspace_id", text("created_at DESC")),
        Index(
            "ix_credit_tx_task",
            "task_id",
            postgresql_where=text("task_id IS NOT NULL"),
        ),
        {"schema": "billing"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    transaction_type: Mapped[str] = mapped_column(Text, nullable=False)
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    amount_credits: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    balance_after_credits: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    fx_rate_usd_to_rub: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


class Plan(Base):
    """Tariff catalog row (global reference table — no per-tenant RLS).

    Seeded by ``billing/0002_plans.py`` with the 6 ADR-008 tiers. Read-only
    from the application (no ORM inserts/updates). Wave 1 enforces trial+solo;
    team/enterprise are catalog-only until multi-cell provisioning lands.
    """

    __tablename__ = "plans"
    __table_args__ = ({"schema": "billing"},)

    slug: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    included_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("0")
    )
    cells_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agents_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soft_cap_credits: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    hard_cap_credits: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    per_task_soft_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("50")
    )
    per_task_hard_credits: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("100")
    )
    per_day_cap_credits: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    trial_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    byok_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    byok_platform_fee_rub: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


class Subscription(Base):
    """Cell↔plan subscription with billing period + trial state.

    Cell-isolated via RLS (``sub_cell_isolation`` USING ``current_cell_id()``).
    One non-canceled subscription per cell (partial-unique index). Wave-1 grants
    are valid within ``period_start..period_end`` only — rollover/expiry deferred.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('trial','active','past_due','canceled')",
            name="subscriptions_status_check",
        ),
        Index(
            "subscriptions_one_active_per_cell",
            "cell_id",
            unique=True,
            postgresql_where=text("status <> 'canceled'"),
        ),
        Index("ix_subscriptions_cell", "cell_id"),
        {"schema": "billing"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    plan_slug: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    period_end: Mapped[datetime] = mapped_column(nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(nullable=True)
    credits_granted_this_period: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
