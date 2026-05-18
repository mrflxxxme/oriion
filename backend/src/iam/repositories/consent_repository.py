"""Consent repository — iam.consents (FZ-152 ledger)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import Consent


class ConsentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        user_id: UUID,
        kind: str,
        version: str,
        ip: str | None,
        user_agent: str | None,
    ) -> Consent:
        row = Consent(
            user_id=user_id,
            kind=kind,
            version=version,
            ip=ip,
            user_agent=user_agent,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_active(self, user_id: UUID, kind: str) -> Consent | None:
        stmt = select(Consent).where(
            Consent.user_id == user_id,
            Consent.kind == kind,
            Consent.revoked_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, user_id: UUID, kind: str) -> None:
        await self._session.execute(
            update(Consent)
            .where(
                Consent.user_id == user_id,
                Consent.kind == kind,
                Consent.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
