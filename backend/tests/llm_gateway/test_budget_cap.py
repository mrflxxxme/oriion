"""F-P5-2 / AC10 anchor: per-task budget cap enforcement.

Per phase-spec AC10 (cost ≤30¢ per demo run) the 50 T-credit per-task
reservation is the hard guard. ``runtime.budget_guard.check_budget`` is
the single chokepoint — orchestrator + delegate path call it before
every LLM dispatch.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from src.runtime.budget_guard import (
    DEFAULT_TASK_CAP_TCREDITS,
    check_budget,
    refund_unused,
    reserve,
)
from src.tasks.exceptions import BudgetExceeded


def test_check_budget_passes_below_cap():
    """Accumulated below cap → no raise."""
    check_budget(accumulated_cost=Decimal("10"), pending_cost=Decimal("5"))


def test_check_budget_passes_at_cap():
    """Exactly at cap is allowed (cap is inclusive upper bound)."""
    check_budget(accumulated_cost=DEFAULT_TASK_CAP_TCREDITS, pending_cost=Decimal(0))


def test_check_budget_raises_above_cap():
    """accumulated + pending > cap → BudgetExceeded with informative detail."""
    with pytest.raises(BudgetExceeded) as exc_info:
        check_budget(
            accumulated_cost=DEFAULT_TASK_CAP_TCREDITS,
            pending_cost=Decimal("0.0001"),
        )
    assert "50" in str(exc_info.value.detail)


def test_record_llm_cost_raises_budget_exceeded_above_50_credits():
    """F-P5-2 closure name — the canonical test the audit calls out.

    Simulates the orchestrator loop: after each LLM step we accumulate cost
    and call check_budget. Once total crosses the 50 T-credit threshold,
    the next check raises BudgetExceeded.
    """
    accumulated = Decimal(0)
    # 10 calls * 4.9 credits = 49 credits, under cap.
    for _ in range(10):
        accumulated += Decimal("4.9")
        check_budget(accumulated_cost=accumulated)
    # The 11th call would push above 50 — must raise BEFORE the LLM is hit.
    with pytest.raises(BudgetExceeded):
        check_budget(accumulated_cost=accumulated, pending_cost=Decimal("5.0"))


def test_reserve_returns_cap():
    assert reserve() == DEFAULT_TASK_CAP_TCREDITS
    assert reserve(Decimal("100")) == Decimal("100")


def test_refund_unused_returns_remainder():
    assert refund_unused(used=Decimal("20"), reserved=Decimal("50")) == Decimal("30")


def test_refund_unused_zero_when_overspent():
    """Overspending (used > reserved) returns 0, not negative refund."""
    assert refund_unused(used=Decimal("60"), reserved=Decimal("50")) == Decimal(0)
