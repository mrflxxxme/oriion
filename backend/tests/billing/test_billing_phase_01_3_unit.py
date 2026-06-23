"""Phase 01.3 billing — pure unit tests (no DB).

- credit_rate_service constants + FX env read.
- BYOK skip-debit / managed-debit split in record_llm_cost (fake session).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.billing.models import CreditTransaction
from src.billing.services.credit_rate_service import get_credit_rate
from src.llm_gateway.models import LLMUsageLog
from src.llm_gateway.services.billing_service import record_llm_cost


def test_credit_rate_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FX_RATE_USD_TO_RUB", raising=False)
    rate = get_credit_rate()
    assert rate.rub_per_credit == Decimal("1")
    assert rate.role_multiplier == Decimal("1")
    assert rate.wave == "0-1"
    assert rate.fx_rate_usd_to_rub == Decimal("100.0")


def test_credit_rate_reads_fx_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FX_RATE_USD_TO_RUB", "92.5")
    assert get_credit_rate().fx_rate_usd_to_rub == Decimal("92.5")


class _FakeAsyncSession:
    """In-memory session: materializes ids + answers SUM queries with 0."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self._next_id = 1

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        for row in self.added:
            if isinstance(row, LLMUsageLog) and row.id is None:
                row.id = self._next_id
                self._next_id += 1

    async def execute(self, _stmt: Any) -> Any:
        scalar_obj = MagicMock()
        scalar_obj.scalar_one = MagicMock(return_value=Decimal(0))
        return scalar_obj


@pytest.mark.asyncio
async def test_byok_call_skips_credit_debit() -> None:
    """AC-01.3.7: a BYOK-paid call writes the usage_log audit row (tagged
    byok_key_id) but NO credit_transactions debit."""
    session = _FakeAsyncSession()
    byok_id = uuid4()
    await record_llm_cost(
        session=session,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        cell_id=uuid4(),
        user_id=None,
        task_id=None,
        provider="deepseek",
        model="deepseek-chat",
        tokens_in=1000,
        tokens_out=500,
        latency_ms=100,
        status="success",
        request_id="req-byok",
        byok_key_id=byok_id,
    )
    usage = [r for r in session.added if isinstance(r, LLMUsageLog)]
    debits = [r for r in session.added if isinstance(r, CreditTransaction)]
    assert len(usage) == 1
    assert usage[0].byok_key_id == byok_id
    assert debits == []


@pytest.mark.asyncio
async def test_null_trial_provisioning_is_noop() -> None:
    """The Null-object default (unit/test mode) silently no-ops."""
    from src.billing.services.subscription_service import NullTrialProvisioningService

    result = await NullTrialProvisioningService().grant_trial(
        cell_id=uuid4(), workspace_id=uuid4(), user_id=uuid4()
    )
    assert result is None


@pytest.mark.asyncio
async def test_managed_call_records_debit() -> None:
    """Managed (no BYOK key) usage still debits credits."""
    session = _FakeAsyncSession()
    await record_llm_cost(
        session=session,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        cell_id=uuid4(),
        user_id=None,
        task_id=None,
        provider="deepseek",
        model="deepseek-chat",
        tokens_in=1000,
        tokens_out=500,
        latency_ms=100,
        status="success",
        request_id="req-managed",
        byok_key_id=None,
    )
    debits = [r for r in session.added if isinstance(r, CreditTransaction)]
    assert len(debits) == 1
    assert debits[0].transaction_type == "debit"
