"""RefreshToken repository — iam.refresh_tokens with OWASP rotation chain."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import RefreshToken, Session


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        session_id: UUID,
        token_hash: str,
        rotation_chain_id: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        row = RefreshToken(
            session_id=session_id,
            token_hash=token_hash,
            rotation_chain_id=rotation_chain_id,
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_used_and_link(
        self,
        token_id: UUID,
        new_token_id: UUID,
    ) -> None:
        """Mark the current row as consumed and link to its successor."""
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(used_at=datetime.now(UTC), rotated_to=new_token_id)
        )

    async def revoke_chain(self, rotation_chain_id: UUID) -> None:
        """Reuse-detection: revoke every token in the chain."""
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.rotation_chain_id == rotation_chain_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_for_session(self, session_id: UUID) -> None:
        """Revoke every active refresh token attached to one session (Phase 01.8
        session-list revoke) so a revoked session's refresh tokens can't rotate."""
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user_except_session(
        self, *, user_id: UUID, keep_session_id: UUID
    ) -> None:
        """Revoke refresh tokens for ALL of the user's sessions except one.

        refresh_tokens has no user_id column — it joins via sessions. The
        subquery scopes to sessions owned by ``user_id`` (the authorization
        boundary) and excludes the caller's current session id.
        """
        owned_sessions = (
            select(Session.id)
            .where(Session.user_id == user_id, Session.id != keep_session_id)
            .scalar_subquery()
        )
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.session_id.in_(owned_sessions),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
