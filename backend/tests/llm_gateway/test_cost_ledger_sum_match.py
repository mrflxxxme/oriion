"""AC4 — atomic 3-currency write sum-check invariant.

For N record_llm_cost calls per cell:
    SUM(credit_transactions.amount_rub) == SUM(llm_usage_log.cost_rub)

Marked `integration` because the canonical test path requires a real
Postgres + RLS context; this unit-tier variant uses an in-memory fake
session and verifies the invariant programmatically across a batch of calls.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.billing.models import CreditTransaction
from src.llm_gateway.models import LLMUsageLog
from src.llm_gateway.services.billing_service import record_llm_cost


class _FakeAsyncSession:
    """In-memory session that materializes id + answers SUM queries with 0."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self._next_id = 1

    def add(self, row: Any) -> None:
        if hasattr(row, "id") and row.id is None:
            # Bigserial-shaped IDs for LLMUsageLog; UUID for CreditTransaction
            if isinstance(row, LLMUsageLog):
                row.id = self._next_id
                self._next_id += 1
            else:
                row.id = uuid4()
        self.added.append(row)

    async def flush(self) -> None:
        for row in self.added:
            if hasattr(row, "id") and row.id is None:
                if isinstance(row, LLMUsageLog):
                    row.id = self._next_id
                    self._next_id += 1
                else:
                    row.id = uuid4()

    async def execute(self, _stmt: Any) -> Any:
        # Always return zero — running balance is unused for the sum-check.
        scalar_obj = MagicMock()
        scalar_obj.scalar_one = MagicMock(return_value=Decimal(0))
        return scalar_obj


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cost_ledger_sum_match() -> None:
    """N atomic writes preserve SUM(amount_rub) == SUM(cost_rub) invariant."""
    session = _FakeAsyncSession()
    workspace_id = uuid4()
    cell_id = uuid4()

    cases = [
        ("deepseek", "deepseek-chat", 1000, 500),
        ("deepseek", "deepseek-reasoner", 200, 800),
        ("yandexgpt", "yandexgpt-pro", 500, 500),
        ("gigachat", "GigaChat-Pro", 300, 700),
        ("openai", "gpt-4o", 100, 100),
    ]

    for idx, (provider, model, tokens_in, tokens_out) in enumerate(cases):
        await record_llm_cost(
            session=session,  # type: ignore[arg-type]
            workspace_id=workspace_id,
            cell_id=cell_id,
            user_id=None,
            task_id=None,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=100 + idx,
            status="success",
            request_id=f"req-{idx}",
        )

    usage_rows = [r for r in session.added if isinstance(r, LLMUsageLog)]
    tx_rows = [r for r in session.added if isinstance(r, CreditTransaction)]
    assert len(usage_rows) == len(cases)
    assert len(tx_rows) == len(cases)

    sum_usage_rub = sum((r.cost_rub for r in usage_rows), Decimal(0))
    sum_tx_rub = sum((r.amount_rub for r in tx_rows), Decimal(0))
    assert (
        sum_usage_rub == sum_tx_rub
    ), f"Sum-check invariant broken: usage={sum_usage_rub} vs tx={sum_tx_rub}"

    # Per-row pairing: each usage row must have a matching tx row with the
    # same cost_rub (atomic-pair guarantee, AC4).
    for usage, tx in zip(usage_rows, tx_rows, strict=True):
        assert usage.cost_rub == tx.amount_rub
        assert usage.fx_rate_usd_to_rub == tx.fx_rate_usd_to_rub
