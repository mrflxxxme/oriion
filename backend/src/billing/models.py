"""SQLAlchemy 2.x model for billing.credit_transactions (Wave 0 SKELETON).

Schema authoritative per contracts/billing/README.md inline DDL section.
Migration: backend/migrations/versions/billing/0001_credit_transactions_skeleton.py
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, Integer, Numeric, Text, text
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
