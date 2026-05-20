"""Per-task budget cap: 50 T-credit reservation per task (AC10 anchor, F-P5-2).

Wave 0 implementation: stateless guard called inline by the orchestrator
before/after each LLM step. Reservation + refund semantics are accounting
metadata rather than a separate ledger row in Wave 0 — full ledger lands
when billing.bill_credit_transaction stabilizes in Wave 1+.
"""

from __future__ import annotations

from decimal import Decimal

from src.tasks.exceptions import BudgetExceeded

DEFAULT_TASK_CAP_TCREDITS = Decimal("50.0000")


def check_budget(
    *,
    accumulated_cost: Decimal,
    pending_cost: Decimal = Decimal(0),
    cap: Decimal = DEFAULT_TASK_CAP_TCREDITS,
) -> None:
    """Raise BudgetExceeded if accumulated + pending exceeds cap.

    Per phase-spec AC10 + F-P5-2: per-task cap of 50 T-credits. The
    orchestrator calls this BEFORE issuing an LLM call with the cost
    estimate as pending_cost, and AFTER with the actual cost included in
    accumulated_cost (so subsequent steps see the new baseline).
    """
    total = accumulated_cost + pending_cost
    if total > cap:
        raise BudgetExceeded(
            f"task cost {total} T-credits exceeds per-task cap {cap}. "
            "Coordinator must trim plan scope or fail-fast to user."
        )


def reserve(cap: Decimal = DEFAULT_TASK_CAP_TCREDITS) -> Decimal:
    """Initial reservation at task start. Wave 0 just echoes the cap; Wave 1
    converts to a real CreditTransaction(kind='reservation')."""
    return cap


def refund_unused(used: Decimal, reserved: Decimal) -> Decimal:
    """Return unused = reserved - used (≥0)."""
    if used >= reserved:
        return Decimal(0)
    return reserved - used
