"""Balance + usage reads over the billing.credit_transactions ledger.

The ledger is the authoritative source: balance/usage are SUM aggregates, not
a stored counter (``balance_after_credits`` is a soft display field only). Every
query also filters by ``cell_id`` — defence-in-depth on top of RLS.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import CreditTransaction

# Transaction types that increase the balance (vs the single 'debit' type).
CREDIT_TYPES: tuple[str, ...] = ("credit", "trial_grant", "refund")


async def _sum_credits(
    session: AsyncSession,
    cell_id: UUID,
    *,
    types: tuple[str, ...],
    since: datetime | None = None,
) -> Decimal:
    stmt = select(func.coalesce(func.sum(CreditTransaction.amount_credits), Decimal(0))).where(
        CreditTransaction.cell_id == cell_id,
        CreditTransaction.transaction_type.in_(list(types)),
    )
    if since is not None:
        stmt = stmt.where(CreditTransaction.created_at >= since)
    return Decimal((await session.execute(stmt)).scalar_one())


async def get_balance(session: AsyncSession, cell_id: UUID) -> Decimal:
    """Net credit balance = SUM(grants/refunds) - SUM(debits) for the cell."""
    credits = await _sum_credits(session, cell_id, types=CREDIT_TYPES)
    debits = await _sum_credits(session, cell_id, types=("debit",))
    return credits - debits


async def get_period_usage(
    session: AsyncSession, cell_id: UUID, *, period_start: datetime
) -> Decimal:
    """Credits consumed (debits) since the subscription period started."""
    return await _sum_credits(session, cell_id, types=("debit",), since=period_start)


async def get_daily_usage(
    session: AsyncSession, cell_id: UUID, *, now: datetime | None = None
) -> Decimal:
    """Credits consumed (debits) since 00:00 UTC of the reference day (R-04)."""
    ref = now or datetime.now(UTC)
    day_start = ref.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return await _sum_credits(session, cell_id, types=("debit",), since=day_start)


async def list_transactions(
    session: AsyncSession,
    cell_id: UUID,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
) -> Sequence[CreditTransaction]:
    """Most-recent-first ledger page for the cell."""
    stmt = select(CreditTransaction).where(CreditTransaction.cell_id == cell_id)
    if date_from is not None:
        stmt = stmt.where(CreditTransaction.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(CreditTransaction.created_at <= date_to)
    stmt = stmt.order_by(CreditTransaction.created_at.desc()).limit(limit)
    return (await session.execute(stmt)).scalars().all()
