"""Session repository — iam.sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        ip: str | None,
        user_agent: str | None,
        ttl_seconds: int,
    ) -> Session:
        row = Session(
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_by_id(self, session_id: UUID) -> Session | None:
        return await self._session.get(Session, session_id)

    async def revoke(self, session_id: UUID) -> None:
        await self._session.execute(
            update(Session)
            .where(Session.id == session_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_for_user(self, *, session_id: UUID, user_id: UUID) -> int:
        """Revoke ONE session, but only if it belongs to ``user_id``.

        The ``user_id`` predicate is the authorization boundary: a user can
        never revoke another user's session even if they guess the id. Returns
        the affected row count (0 = not found / not owned / already revoked).
        """
        result = await self._session.execute(
            update(Session)
            .where(
                Session.id == session_id,
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        # execute() of an UPDATE returns a CursorResult carrying rowcount.
        return int(cast("CursorResult[Any]", result).rowcount)

    async def revoke_all_others_for_user(self, *, user_id: UUID, keep_session_id: UUID) -> None:
        """Revoke every active session for the user EXCEPT ``keep_session_id``
        (the caller's current session) — 'log out everywhere else'."""
        await self._session.execute(
            update(Session)
            .where(
                Session.user_id == user_id,
                Session.id != keep_session_id,
                Session.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def list_active_for_user(self, user_id: UUID) -> list[Session]:
        stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .order_by(Session.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())
