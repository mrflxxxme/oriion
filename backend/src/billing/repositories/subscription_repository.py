"""Subscription repository — billing.subscriptions (cell-isolated via RLS)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import Subscription


class SubscriptionRepository:
    """Per-cell subscription access. RLS scopes every query to the active cell."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_cell(self, cell_id: UUID) -> Subscription | None:
        """The single non-canceled subscription for a cell, if any."""
        stmt = select(Subscription).where(
            Subscription.cell_id == cell_id,
            Subscription.status != "canceled",
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        plan_slug: str,
        status: str,
        period_start: datetime,
        period_end: datetime,
        trial_ends_at: datetime | None,
        credits_granted_this_period: Decimal,
    ) -> Subscription:
        row = Subscription(
            cell_id=cell_id,
            workspace_id=workspace_id,
            plan_slug=plan_slug,
            status=status,
            period_start=period_start,
            period_end=period_end,
            trial_ends_at=trial_ends_at,
            credits_granted_this_period=credits_granted_this_period,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_status(self, subscription_id: UUID, status: str) -> None:
        await self._session.execute(
            update(Subscription).where(Subscription.id == subscription_id).values(status=status)
        )
