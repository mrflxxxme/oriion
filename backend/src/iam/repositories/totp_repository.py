"""TOTP repositories — iam.totp_credentials + iam.totp_backup_codes (Phase 01.8).

The credential row stores the shared secret ENCRYPTED (``secret_encrypted``);
encryption/decryption is the service's job (KMS provider) — this repo only
persists opaque bytes. Backup codes are stored SHA-256 hashed (service hashes
before calling ``add_backup_codes``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.models import TotpBackupCode, TotpCredential


class TotpCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, secret_encrypted: bytes) -> TotpCredential:
        row = TotpCredential(user_id=user_id, secret_encrypted=secret_encrypted)
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_by_user(self, user_id: UUID) -> TotpCredential | None:
        stmt = select(TotpCredential).where(TotpCredential.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find_active_by_user(self, user_id: UUID) -> TotpCredential | None:
        """A credential that actually gates login: confirmed AND not disabled."""
        stmt = select(TotpCredential).where(
            TotpCredential.user_id == user_id,
            TotpCredential.confirmed_at.is_not(None),
            TotpCredential.disabled_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def confirm(self, credential_id: UUID) -> None:
        await self._session.execute(
            update(TotpCredential)
            .where(TotpCredential.id == credential_id)
            .values(confirmed_at=datetime.now(UTC))
        )

    async def disable(self, credential_id: UUID) -> None:
        await self._session.execute(
            update(TotpCredential)
            .where(TotpCredential.id == credential_id)
            .values(disabled_at=datetime.now(UTC))
        )

    async def delete_for_user(self, user_id: UUID) -> None:
        """Remove any existing credential (+ cascade backup codes) so a fresh
        enroll starts clean. Used when re-enrolling over a pending/disabled row."""
        await self._session.execute(delete(TotpCredential).where(TotpCredential.user_id == user_id))


class TotpBackupCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_batch(self, *, credential_id: UUID, code_hashes: Sequence[str]) -> None:
        for code_hash in code_hashes:
            self._session.add(TotpBackupCode(credential_id=credential_id, code_hash=code_hash))
        await self._session.flush()

    async def find_unused_by_hash(
        self, *, credential_id: UUID, code_hash: str
    ) -> TotpBackupCode | None:
        stmt = select(TotpBackupCode).where(
            TotpBackupCode.credential_id == credential_id,
            TotpBackupCode.code_hash == code_hash,
            TotpBackupCode.used_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_used(self, code_id: UUID) -> None:
        await self._session.execute(
            update(TotpBackupCode)
            .where(TotpBackupCode.id == code_id)
            .values(used_at=datetime.now(UTC))
        )

    async def delete_unused_for_credential(self, credential_id: UUID) -> None:
        await self._session.execute(
            delete(TotpBackupCode).where(
                TotpBackupCode.credential_id == credential_id,
                TotpBackupCode.used_at.is_(None),
            )
        )
