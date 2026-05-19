"""Unit tests for billing_service.record_llm_cost — atomic 3-currency write."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import structlog
from src.billing.models import CreditTransaction
from src.llm_gateway.models import LLMUsageLog
from src.llm_gateway.services.billing_service import record_llm_cost


class _FakeAsyncSession:
    """Minimal AsyncSession stand-in.

    Captures `session.add(row)` calls in `added` and answers SUM-aggregate
    `execute()` calls with a configurable return value so the running-balance
    helper sees a deterministic prior balance.
    """

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flushed = 0
        self._sum_returns: list[Decimal] = [Decimal(0), Decimal(0)]

    def add(self, row: Any) -> None:
        # Materialize `id` so the billing service can reference it.
        if hasattr(row, "id") and row.id is None:
            row.id = len(self.added) + 1
        self.added.append(row)

    async def flush(self) -> None:
        self.flushed += 1
        # Materialize IDs on objects added without one set.
        for row in self.added:
            if hasattr(row, "id") and row.id is None:
                row.id = len(self.added)

    async def execute(self, _stmt: Any) -> Any:
        # The billing service calls execute twice (credits then debits).
        retval = self._sum_returns.pop(0) if self._sum_returns else Decimal(0)
        scalar_obj = MagicMock()
        scalar_obj.scalar_one = MagicMock(return_value=retval)
        return scalar_obj


@pytest.mark.asyncio
async def test_record_llm_cost_inserts_both_rows_and_emits_event() -> None:
    session = _FakeAsyncSession()
    workspace_id = uuid4()
    cell_id = uuid4()
    user_id = uuid4()
    request_id = "req-test-001"

    with structlog.testing.capture_logs() as logs:
        cost_usd, cost_rub = await record_llm_cost(
            session=session,  # type: ignore[arg-type]
            workspace_id=workspace_id,
            cell_id=cell_id,
            user_id=user_id,
            task_id=None,
            provider="deepseek",
            model="deepseek-chat",
            tokens_in=1000,
            tokens_out=1000,
            latency_ms=420,
            status="success",
            request_id=request_id,
        )

    # Both rows queued in the same transaction.
    usage_rows = [r for r in session.added if isinstance(r, LLMUsageLog)]
    tx_rows = [r for r in session.added if isinstance(r, CreditTransaction)]
    assert len(usage_rows) == 1
    assert len(tx_rows) == 1

    usage_row = usage_rows[0]
    tx_row = tx_rows[0]

    # cost_rub equality — sum-check invariant.
    assert usage_row.cost_rub == cost_rub
    assert tx_row.amount_rub == cost_rub
    # Wave 0 invariant: 1 credit = 1 RUB.
    assert tx_row.amount_credits == cost_rub
    # FX rate pinned on both rows.
    assert usage_row.fx_rate_usd_to_rub == tx_row.fx_rate_usd_to_rub
    # USD/RUB values returned by the service match the rows.
    assert usage_row.cost_usd == cost_usd
    assert tx_row.transaction_type == "debit"
    assert tx_row.provider == "deepseek"
    assert tx_row.model == "deepseek-chat"

    # cloudevent emission.
    ce = next(log for log in logs if log.get("ce_type", "").endswith("request.completed.v1"))
    assert ce["data"]["status"] == "success"
    assert ce["data"]["provider_slug"] == "deepseek"
    assert ce["data"]["request_id"] == request_id


@pytest.mark.asyncio
async def test_record_llm_cost_handles_zero_priced_unknown_model() -> None:
    """Unknown model → cost=0; ledger still writes both rows."""
    session = _FakeAsyncSession()

    cost_usd, cost_rub = await record_llm_cost(
        session=session,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        cell_id=uuid4(),
        user_id=None,
        task_id=None,
        provider="exotic-provider",
        model="unknown-model",
        tokens_in=10,
        tokens_out=10,
        latency_ms=100,
        status="success",
        request_id="req-zero",
    )
    assert cost_usd == Decimal(0)
    assert cost_rub == Decimal(0)
    usage_rows = [r for r in session.added if isinstance(r, LLMUsageLog)]
    tx_rows = [r for r in session.added if isinstance(r, CreditTransaction)]
    assert len(usage_rows) == 1
    assert len(tx_rows) == 1
    assert tx_rows[0].amount_rub == Decimal(0)
