"""Atomic 3-currency cost ledger writer.

Per llm-gateway invariant #7 (README.md), ``record_llm_cost`` MUST write
both ``llm_gateway.llm_usage_log`` and ``billing.credit_transactions`` in
the same transaction so the sum-check invariant holds:

    SUM(credit_transactions.amount_rub) == SUM(llm_usage_log.cost_rub)
    per cell

Wave 0 invariant: 1 credit = 1 RUB (per contracts/billing/README.md), so
``amount_credits = amount_rub``. Wave 2+ swaps this via the pricing_table.

`balance_after_credits` is derived by summing prior debits within the same
cell — this is a soft accounting field useful for UI display only; the
authoritative source remains the SUM aggregate.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import CreditTransaction
from src.llm_gateway import events as gateway_events
from src.llm_gateway.models import LLMUsageLog
from src.llm_gateway.services.pricing_service import (
    calculate_cost_usd_and_rub,
    get_fx_rate,
)


async def _running_balance_after_debit(
    session: AsyncSession,
    cell_id: UUID,
    new_amount_rub: Decimal,
) -> Decimal:
    """Compute balance_after_credits = -SUM(debits) + SUM(credits) for this cell.

    Wave 0 cells start with a `trial_grant` row; this function reads existing
    rows and applies the new debit. Negative balances are allowed (soft-cap
    per invariant #4 — hard cap enforced via cost-budget kill-switch).
    """
    sum_credits_stmt = select(
        func.coalesce(func.sum(CreditTransaction.amount_credits), Decimal(0))
    ).where(
        CreditTransaction.cell_id == cell_id,
        CreditTransaction.transaction_type.in_(["credit", "trial_grant", "refund"]),
    )
    sum_debits_stmt = select(
        func.coalesce(func.sum(CreditTransaction.amount_credits), Decimal(0))
    ).where(
        CreditTransaction.cell_id == cell_id,
        CreditTransaction.transaction_type == "debit",
    )
    credits_total = (await session.execute(sum_credits_stmt)).scalar_one()
    debits_total = (await session.execute(sum_debits_stmt)).scalar_one()
    return Decimal(credits_total) - Decimal(debits_total) - new_amount_rub


async def record_llm_cost(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    cell_id: UUID,
    user_id: UUID | None,
    task_id: UUID | None,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    status: str,
    request_id: str,
    byok_key_id: UUID | None = None,
) -> tuple[Decimal, Decimal]:
    """Insert ``llm_usage_log`` + ``credit_transactions`` rows atomically.

    Args:
        session: AsyncSession bound to an outer transaction (caller commits).
            We deliberately do NOT commit here — the caller's request handler
            owns the transaction boundary (see invariant #2 / synchronous
            logging in llm-gateway/README.md).
        status: 'success' | 'error' | 'timeout' | 'rate_limited'

    Returns:
        (cost_usd, cost_rub) as Decimal — useful for caller to attach to its
        own response envelope.

    Side effects:
        Emits ``oriion.llm-gateway.request.completed.v1`` cloudevent AFTER
        the SQL INSERTs are queued on the session (still inside the
        transaction; commit is caller's responsibility).
    """
    fx_rate = get_fx_rate()
    cost_usd, cost_rub = calculate_cost_usd_and_rub(provider, model, tokens_in, tokens_out, fx_rate)

    # 1) llm_usage_log row — append-only audit.
    usage_row = LLMUsageLog(
        workspace_id=workspace_id,
        cell_id=cell_id,
        task_id=task_id,
        byok_key_id=byok_key_id,
        provider_slug=provider,
        model_name=model,
        request_id=request_id,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        cached_input_tokens=0,
        cost_usd=cost_usd,
        cost_rub=cost_rub,
        fx_rate_usd_to_rub=fx_rate,
        latency_ms=latency_ms,
        status=status,
    )
    session.add(usage_row)
    # Flush so usage_row.id is materialized (used as payload reference).
    await session.flush()

    # 2) billing.credit_transactions row — atomic partner. 1 credit = 1 RUB.
    amount_credits = cost_rub
    balance_after = await _running_balance_after_debit(session, cell_id, cost_rub)

    tx_row = CreditTransaction(
        cell_id=cell_id,
        workspace_id=workspace_id,
        user_id=user_id,
        task_id=task_id,
        transaction_type="debit",
        amount_rub=cost_rub,
        amount_credits=amount_credits,
        balance_after_credits=balance_after,
        fx_rate_usd_to_rub=fx_rate,
        provider=provider,
        model=model,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        payload={
            "llm_usage_log_id": usage_row.id,
            "request_id": request_id,
            "byok_key_id": str(byok_key_id) if byok_key_id else None,
        },
    )
    session.add(tx_row)
    await session.flush()

    # 3) cloudevent — log-only Wave 0 (transport: structlog tag).
    await gateway_events.emit_request_completed(
        request_id=request_id,
        workspace_id=workspace_id,
        cell_id=cell_id,
        task_id=task_id,
        byok_key_id=byok_key_id,
        provider_slug=provider,
        model=model,
        status=status,
        cost_usd=cost_usd,
        cost_rub=cost_rub,
        fx_rate_usd_to_rub=fx_rate,
        latency_ms=latency_ms,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
    )

    return cost_usd, cost_rub
