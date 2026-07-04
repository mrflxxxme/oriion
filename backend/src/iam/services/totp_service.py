"""TOTP (2FA) service — enroll / confirm / verify / disable + backup codes.

Phase 01.8. RFC-6238 TOTP via ``pyotp``. Security model:

  * The shared secret is SENSITIVE. It is encrypted at rest with the KMS
    provider (AES-256-GCM blob, see llm_gateway.services.kms_provider) — the DB
    only ever holds ciphertext. The plaintext base32 secret leaves the service
    exactly once: in the enroll response (so the user can add it to an app).
    It is NEVER logged.
  * Codes are verified with ``pyotp.TOTP.verify(..., valid_window=1)`` — a ±1
    step (30s) drift tolerance, no wider (replay/brute-force surface).
  * Backup codes are single-use, SHA-256 hashed at rest (constant-time compare
    via the unique-hash lookup), returned in plaintext exactly once at confirm.

Enrollment is two-phase: enroll creates a PENDING row (confirmed_at NULL);
confirm activates it only after the user proves possession with a live code.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from uuid import UUID

import pyotp

from src.iam.exceptions import (
    TotpAlreadyEnabled,
    TotpInvalidCode,
    TotpNotEnabled,
    TotpNotEnrolled,
)
from src.iam.repositories.totp_repository import (
    TotpBackupCodeRepository,
    TotpCredentialRepository,
)
from src.iam.repositories.user_repository import UserRepository
from src.llm_gateway.services.kms_provider import KMSProvider

_ISSUER = "TEAMLY"
_BACKUP_CODE_COUNT = 10
_BACKUP_CODE_BYTES = 5  # 10 hex chars per code


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_backup_code() -> str:
    # 10-char lowercase-hex code; formatted xxxxx-xxxxx for readability.
    raw = secrets.token_hex(_BACKUP_CODE_BYTES)
    return f"{raw[:5]}-{raw[5:]}"


@dataclass(frozen=True, slots=True)
class TotpEnrollment:
    secret: str
    provisioning_uri: str


class TotpService:
    """2FA lifecycle. Holds a KMS provider for at-rest secret encryption."""

    def __init__(
        self,
        *,
        credential_repo: TotpCredentialRepository,
        backup_code_repo: TotpBackupCodeRepository,
        user_repo: UserRepository,
        kms: KMSProvider,
    ) -> None:
        self._credential_repo = credential_repo
        self._backup_code_repo = backup_code_repo
        self._user_repo = user_repo
        self._kms = kms

    # ── enroll ──────────────────────────────────────────────────────────

    async def enroll(self, *, user_id: UUID, account_label: str) -> TotpEnrollment:
        """Begin enrollment: generate a secret, persist it ENCRYPTED as a
        pending credential, and return the base32 secret + otpauth URI.

        Idempotent-ish: if an ACTIVE credential exists, refuse (409). If only a
        PENDING/disabled row exists, it is replaced so a stalled enroll can
        restart cleanly.
        """
        existing = await self._credential_repo.find_by_user(user_id)
        if (
            existing is not None
            and existing.confirmed_at is not None
            and existing.disabled_at is None
        ):
            raise TotpAlreadyEnabled()
        if existing is not None:
            # Pending or disabled → clear it (cascades backup codes) and re-enroll.
            await self._credential_repo.delete_for_user(user_id)

        secret = pyotp.random_base32()
        secret_encrypted = await self._kms.encrypt(secret.encode("utf-8"))
        await self._credential_repo.create(user_id=user_id, secret_encrypted=secret_encrypted)

        uri = pyotp.TOTP(secret).provisioning_uri(name=account_label, issuer_name=_ISSUER)
        return TotpEnrollment(secret=secret, provisioning_uri=uri)

    # ── confirm ─────────────────────────────────────────────────────────

    async def confirm(self, *, user_id: UUID, code: str) -> list[str]:
        """Activate a pending enrollment after verifying the first live code.

        Returns freshly-generated single-use backup codes (plaintext, once).
        """
        cred = await self._credential_repo.find_by_user(user_id)
        if cred is None or cred.disabled_at is not None:
            raise TotpNotEnrolled()
        if cred.confirmed_at is not None:
            raise TotpAlreadyEnabled()

        secret = (await self._kms.decrypt(cred.secret_encrypted)).decode("utf-8")
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            raise TotpInvalidCode()

        await self._credential_repo.confirm(cred.id)

        # Issue a fresh batch of backup codes.
        plaintext_codes = [_new_backup_code() for _ in range(_BACKUP_CODE_COUNT)]
        await self._backup_code_repo.add_batch(
            credential_id=cred.id,
            code_hashes=[_sha256_hex(c) for c in plaintext_codes],
        )
        return plaintext_codes

    # ── verify (login second factor) ────────────────────────────────────

    async def verify_for_login(self, *, user_id: UUID, code: str) -> bool:
        """Return True iff ``code`` is a valid current TOTP OR an unused backup
        code for the user's ACTIVE credential. A matched backup code is consumed.

        Returns False (never raises) so the caller controls the auth-failure
        surface; a user without active 2FA also returns False.
        """
        cred = await self._credential_repo.find_active_by_user(user_id)
        if cred is None:
            return False

        secret = (await self._kms.decrypt(cred.secret_encrypted)).decode("utf-8")
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            return True

        # Fall back to single-use backup codes.
        code_hash = _sha256_hex(code.strip())
        backup = await self._backup_code_repo.find_unused_by_hash(
            credential_id=cred.id, code_hash=code_hash
        )
        if backup is None:
            return False
        await self._backup_code_repo.mark_used(backup.id)
        return True

    async def is_enabled(self, user_id: UUID) -> bool:
        return await self._credential_repo.find_active_by_user(user_id) is not None

    # ── disable ─────────────────────────────────────────────────────────

    async def disable(self, *, user_id: UUID, code: str) -> None:
        """Turn 2FA off — but only after proving possession with a live code or
        backup code (so a hijacked, still-authenticated session cannot silently
        strip the second factor without the authenticator)."""
        cred = await self._credential_repo.find_active_by_user(user_id)
        if cred is None:
            raise TotpNotEnabled()
        if not await self.verify_for_login(user_id=user_id, code=code):
            raise TotpInvalidCode()
        await self._credential_repo.disable(cred.id)
        await self._backup_code_repo.delete_unused_for_credential(cred.id)
