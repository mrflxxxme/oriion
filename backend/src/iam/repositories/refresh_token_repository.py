"""RefreshToken repository — iam.refresh_tokens with OWASP rotation chain."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import RefreshToken


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
