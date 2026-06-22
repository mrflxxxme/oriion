"""Plan repository — billing.plans tariff catalog (read-only)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import Plan


class PlanRepository:
    """Read-only access to the global tariff catalog.

    The catalog is a global reference table (no RLS); rows are seeded by
    ``billing/0002_plans.py`` and never mutated at runtime.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, slug: str) -> Plan | None:
        stmt = select(Plan).where(Plan.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_active(self) -> Sequence[Plan]:
        """Self-serve-selectable tariffs, cheapest first."""
        stmt = select(Plan).where(Plan.active.is_(True)).order_by(Plan.price_rub.asc().nulls_last())
        return (await self._session.execute(stmt)).scalars().all()

    async def list_all(self) -> Sequence[Plan]:
        stmt = select(Plan).order_by(Plan.price_rub.asc().nulls_last())
        return (await self._session.execute(stmt)).scalars().all()
