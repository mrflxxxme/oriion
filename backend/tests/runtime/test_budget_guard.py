"""Per-task budget cap — check_budget, reserve, refund_unused.

AC10 anchor: 50 T-credit cap per task. BudgetExceeded fires when total
exceeds; refund returns unused difference for accounting.
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


class TestCheckBudget:
    def test_within_cap_passes(self) -> None:
        check_budget(accumulated_cost=Decimal("30"), pending_cost=Decimal("10"))

    def test_at_exact_cap_passes(self) -> None:
        """50 = cap; not > cap so passes."""
        check_budget(accumulated_cost=Decimal("25"), pending_cost=Decimal("25"))

    def test_over_cap_raises(self) -> None:
        with pytest.raises(BudgetExceeded) as exc:
            check_budget(accumulated_cost=Decimal("49"), pending_cost=Decimal("2"))
        assert "exceeds per-task cap" in str(exc.value)

    def test_pending_only_over_cap_raises(self) -> None:
        with pytest.raises(BudgetExceeded):
            check_budget(accumulated_cost=Decimal(0), pending_cost=Decimal("51"))

    def test_custom_cap_honoured(self) -> None:
        check_budget(accumulated_cost=Decimal("9"), cap=Decimal("10"))
        with pytest.raises(BudgetExceeded):
            check_budget(accumulated_cost=Decimal("11"), cap=Decimal("10"))

    def test_no_pending_default(self) -> None:
        check_budget(accumulated_cost=Decimal("49"))  # pending=0 default
        with pytest.raises(BudgetExceeded):
            check_budget(accumulated_cost=Decimal("51"))


class TestReserve:
    def test_default_cap(self) -> None:
        assert reserve() == DEFAULT_TASK_CAP_TCREDITS

    def test_custom_cap(self) -> None:
        assert reserve(cap=Decimal("100")) == Decimal("100")


class TestRefundUnused:
    def test_refund_partial(self) -> None:
        assert refund_unused(used=Decimal("30"), reserved=Decimal("50")) == Decimal("20")

    def test_refund_zero_when_fully_used(self) -> None:
        assert refund_unused(used=Decimal("50"), reserved=Decimal("50")) == Decimal(0)

    def test_refund_zero_when_overspent(self) -> None:
        """Over-budget (used > reserved) — refund stays 0, not negative."""
        assert refund_unused(used=Decimal("60"), reserved=Decimal("50")) == Decimal(0)

    def test_refund_full_when_unused(self) -> None:
        assert refund_unused(used=Decimal(0), reserved=Decimal("50")) == Decimal("50")
