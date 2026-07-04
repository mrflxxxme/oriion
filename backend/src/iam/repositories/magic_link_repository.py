"""MagicLinkToken repository — iam.magic_link_tokens (Phase 01.8).

Copies the email-verification token idiom: SHA-256 hash at rest, single-use,
short TTL. Plaintext lives only in the email (never persisted here).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import MagicLinkToken


class MagicLinkTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> MagicLinkToken:
        row = MagicLinkToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_active_by_hash(self, token_hash: str) -> MagicLinkToken | None:
        from sqlalchemy import select

        stmt = select(MagicLinkToken).where(
            MagicLinkToken.token_hash == token_hash,
            MagicLinkToken.used_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_used(self, token_id: UUID) -> None:
        await self._session.execute(
            update(MagicLinkToken)
            .where(MagicLinkToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )

    async def revoke_unused_for_user(self, user_id: UUID) -> None:
        """Re-requesting a magic link invalidates prior unused ones."""
        await self._session.execute(
            update(MagicLinkToken)
            .where(
                MagicLinkToken.user_id == user_id,
                MagicLinkToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
