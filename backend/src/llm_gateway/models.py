"""SQLAlchemy 2.x models for llm_gateway.

Schema authoritative per contracts/llm-gateway/schema.sql (ADR-024).
Tables live under PostgreSQL schema ``llm_gateway``. Migrations:
  backend/migrations/versions/llm_gateway/0001_..0003_*.py
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base


class LLMProviderConfig(Base):
    """Static registry of supported LLM providers (DDL row-seeded by 0001 migration)."""

    __tablename__ = "llm_provider_config"
    __table_args__ = (
        Index(
            "idx_llm_provider_config_active",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
        {"schema": "llm_gateway"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    provider_slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    default_model: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_byok_supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    supported_features: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


class BYOKKey(Base):
    """Per-workspace BYOK key custody. AES-256-GCM ciphertext only."""

    __tablename__ = "byok_keys"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider_slug",
            "label",
            name="byok_keys_unique_label",
        ),
        Index(
            "idx_byok_keys_workspace_active",
            "workspace_id",
            postgresql_where=text("is_active = true AND revoked_at IS NULL"),
        ),
        {"schema": "llm_gateway"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("multitenancy.workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_slug: Mapped[str] = mapped_column(
        Text,
        ForeignKey("llm_gateway.llm_provider_config.provider_slug"),
        nullable=False,
    )
    key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    monthly_quota_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    monthly_used_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)


class LLMUsageLog(Base):
    """Append-only audit log of every LLM call routed by the gateway.

    Three money columns per ADR-018 amendment (2026-05-19):
        cost_usd            — provider native; invoice reconciliation source
        cost_rub            — customer-facing settlement; pairs with
                              billing.credit_transactions.amount_rub
        fx_rate_usd_to_rub  — pinned at request time for audit reproducibility
    """

    __tablename__ = "llm_usage_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success','error','timeout','rate_limited')",
            name="llm_usage_log_status_check",
        ),
        Index(
            "idx_llm_usage_log_workspace_time",
            "workspace_id",
            text("created_at DESC"),
        ),
        Index(
            "idx_llm_usage_log_byok_time",
            "byok_key_id",
            text("created_at DESC"),
            postgresql_where=text("byok_key_id IS NOT NULL"),
        ),
        Index(
            "idx_llm_usage_log_cell_time",
            "cell_id",
            text("created_at DESC"),
        ),
        Index(
            "idx_llm_usage_log_task",
            "task_id",
            postgresql_where=text("task_id IS NOT NULL"),
        ),
        Index(
            "idx_llm_usage_log_provider_time",
            "provider_slug",
            text("created_at DESC"),
        ),
        {"schema": "llm_gateway"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    byok_key_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("llm_gateway.byok_keys.id"),
        nullable=True,
    )
    provider_slug: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cached_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default=text("0")
    )
    cost_rub: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default=text("0")
    )
    fx_rate_usd_to_rub: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default=text("0")
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
