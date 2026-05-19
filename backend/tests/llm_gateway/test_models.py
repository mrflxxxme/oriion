"""Unit tests — SQLAlchemy models compile + have expected table metadata.

These tests do NOT touch Postgres; they only validate that the model
metadata (table name, schema, columns) matches the contract DDL so a future
divergence is caught early.
"""

from __future__ import annotations

from src.billing.models import CreditTransaction
from src.llm_gateway.models import BYOKKey, LLMProviderConfig, LLMUsageLog


def test_llm_provider_config_table_metadata() -> None:
    assert LLMProviderConfig.__tablename__ == "llm_provider_config"
    assert LLMProviderConfig.__table__.schema == "llm_gateway"
    cols = {c.name for c in LLMProviderConfig.__table__.columns}
    assert {
        "id",
        "provider_slug",
        "display_name",
        "default_model",
        "base_url",
        "is_byok_supported",
        "is_active",
        "supported_features",
        "created_at",
        "updated_at",
    } <= cols


def test_byok_keys_table_metadata() -> None:
    assert BYOKKey.__tablename__ == "byok_keys"
    assert BYOKKey.__table__.schema == "llm_gateway"
    cols = {c.name for c in BYOKKey.__table__.columns}
    assert "key_encrypted" in cols
    assert "key_fingerprint" in cols
    assert "workspace_id" in cols


def test_llm_usage_log_three_money_columns() -> None:
    """ADR-018 amendment 2026-05-19: three money columns."""
    assert LLMUsageLog.__tablename__ == "llm_usage_log"
    cols = {c.name for c in LLMUsageLog.__table__.columns}
    assert "cost_usd" in cols
    assert "cost_rub" in cols
    assert "fx_rate_usd_to_rub" in cols


def test_credit_transactions_metadata() -> None:
    assert CreditTransaction.__tablename__ == "credit_transactions"
    assert CreditTransaction.__table__.schema == "billing"
    cols = {c.name for c in CreditTransaction.__table__.columns}
    assert {
        "id",
        "cell_id",
        "workspace_id",
        "transaction_type",
        "amount_rub",
        "amount_credits",
        "balance_after_credits",
        "fx_rate_usd_to_rub",
        "provider",
        "model",
        "tokens_input",
        "tokens_output",
        "payload",
        "created_at",
    } <= cols
