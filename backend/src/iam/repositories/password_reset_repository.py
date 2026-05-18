"""PasswordResetToken repository — iam.password_reset_tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import PasswordResetToken


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        reset_chain_id: UUID,
        expires_at: datetime,
    ) -> PasswordResetToken:
        row = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            reset_chain_id=reset_chain_id,
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_used(self, token_id: UUID) -> None:
        await self._session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )

    async def revoke_chain(self, reset_chain_id: UUID) -> None:
        """Reuse-detection: revoke the entire reset_chain_id."""
        await self._session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.reset_chain_id == reset_chain_id,
                PasswordResetToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_unused_for_user(self, user_id: UUID) -> None:
        """forgot-password called twice: invalidate prior unused tokens."""
        await self._session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
