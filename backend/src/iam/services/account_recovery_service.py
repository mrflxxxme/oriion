"""Account-recovery flows — email-verification + password-reset.

Extracted from ``AuthService`` (file-size canon split) into a focused
collaborator. ``AuthService`` wires one of these per request (see
``iam/deps.py``) and exposes the four public methods as thin facade
delegators so routers/tests keep calling them on the auth service unchanged:

    verify_email          — POST /auth/verify-email
    resend_verification   — POST /auth/resend-verification (anti-enum 202)
    forgot_password       — POST /auth/forgot-password     (anti-enum 202)
    reset_password        — POST /auth/reset-password

The service holds the request's AsyncSession so ``emit_audit_event`` inserts
participate in the request's outer TX — identical to the pre-split behavior.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.services.audit_service import emit_audit_event
from src.iam import events
from src.iam.exceptions import (
    RateLimitExceeded,
    TokenNotFound,
)
from src.iam.repositories.email_verification_repository import (
    EmailVerificationTokenRepository,
)
from src.iam.repositories.password_reset_repository import PasswordResetTokenRepository
from src.iam.repositories.session_repository import SessionRepository
from src.iam.repositories.user_repository import UserRepository
from src.iam.services.email_service import EmailSender
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService

# Token TTLs per contract README invariants 7+8
EMAIL_VERIFICATION_TTL_SECONDS = 24 * 3600  # 24h
PASSWORD_RESET_TTL_SECONDS = 3600  # 1h


def _hash_token_plaintext(plaintext: str) -> str:
    import hashlib

    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _new_token_plaintext() -> str:
    return secrets.token_urlsafe(32)


class AccountRecoveryService:
    """Email-verification + password-reset flows for ``AuthService``."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        email_verif_repo: EmailVerificationTokenRepository,
        password_reset_repo: PasswordResetTokenRepository,
        password_service: PasswordService,
        rate_limit_service: RateLimitService,
        email_sender: EmailSender,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._session_repo = session_repo
        self._email_verif_repo = email_verif_repo
        self._password_reset_repo = password_reset_repo
        self._password_service = password_service
        self._rate_limit_service = rate_limit_service
        self._email_sender = email_sender

    # ── verify-email ────────────────────────────────────────────────────

    async def verify_email(self, plaintext_token: str) -> None:
        token_hash = _hash_token_plaintext(plaintext_token)
        row = await self._email_verif_repo.find_active_by_hash(token_hash)
        if row is None or row.expires_at < datetime.now(UTC):
            raise TokenNotFound()
        await self._email_verif_repo.mark_used(row.id)
        await self._user_repo.mark_email_verified(row.user_id)
        verified_at = datetime.now(UTC)
        await events.emit_email_verified(user_id=row.user_id, verified_at=verified_at)
        await emit_audit_event(
            actor_type="user",
            actor_id=row.user_id,
            action="iam.user.email_verified",
            resource_type="user",
            resource_id=row.user_id,
            payload=None,
            session=self._session,
        )

    # ── resend-verification (anti-enum 202) ─────────────────────────────

    async def resend_verification(
        self, email: str, *, ip: str | None, user_agent: str | None
    ) -> None:
        if ip:
            verdict = await self._rate_limit_service.check_and_increment(
                scope="resend", ip=ip, email=email
            )
            if not verdict.allowed:
                raise RateLimitExceeded(retry_after=verdict.retry_after)

        user = await self._user_repo.find_by_email(email)
        if user is None or user.email_verified_at is not None:
            return  # anti-enum: do not signal existence

        await self._email_verif_repo.revoke_unused_for_user(user.id)
        plaintext = _new_token_plaintext()
        expires_at = datetime.now(UTC) + timedelta(seconds=EMAIL_VERIFICATION_TTL_SECONDS)
        row = await self._email_verif_repo.create(
            user_id=user.id,
            token_hash=_hash_token_plaintext(plaintext),
            expires_at=expires_at,
        )
        await self._email_sender.send_verification_email(
            to=user.email, token=plaintext, expires_at=expires_at
        )
        await events.emit_email_verification_requested(
            user_id=user.id,
            email=user.email,
            token_id=row.id,
            expires_at=expires_at,
        )

    # ── forgot-password (anti-enum 202) ─────────────────────────────────

    async def forgot_password(self, email: str, *, ip: str | None, user_agent: str | None) -> None:
        if ip:
            verdict = await self._rate_limit_service.check_and_increment(
                scope="forgot", ip=ip, email=email
            )
            if not verdict.allowed:
                raise RateLimitExceeded(retry_after=verdict.retry_after)

        user = await self._user_repo.find_by_email(email)
        if user is None:
            return  # anti-enum

        await self._password_reset_repo.revoke_unused_for_user(user.id)
        plaintext = _new_token_plaintext()
        expires_at = datetime.now(UTC) + timedelta(seconds=PASSWORD_RESET_TTL_SECONDS)
        chain_id = uuid4()
        row = await self._password_reset_repo.create(
            user_id=user.id,
            token_hash=_hash_token_plaintext(plaintext),
            reset_chain_id=chain_id,
            expires_at=expires_at,
        )
        await self._email_sender.send_password_reset_email(
            to=user.email, token=plaintext, expires_at=expires_at
        )
        await events.emit_password_reset_requested(
            user_id=user.id,
            token_id=row.id,
            reset_chain_id=chain_id,
            expires_at=expires_at,
        )

    # ── reset-password ──────────────────────────────────────────────────

    async def reset_password(self, plaintext_token: str, new_password: str) -> None:
        token_hash = _hash_token_plaintext(plaintext_token)
        row = await self._password_reset_repo.find_by_hash(token_hash)
        if row is None or row.revoked_at is not None or row.expires_at < datetime.now(UTC):
            raise TokenNotFound()

        # Reuse detection: a consumed token presented again → chain-revoke
        if row.used_at is not None:
            await self._password_reset_repo.revoke_chain(row.reset_chain_id)
            await self._session_repo.revoke_all_for_user(row.user_id)
            await emit_audit_event(
                actor_type="system",
                actor_id=row.user_id,
                action="iam.auth.reset_reuse_detected",
                resource_type="user",
                resource_id=row.user_id,
                payload={"reset_chain_id": str(row.reset_chain_id)},
                session=self._session,
            )
            raise TokenNotFound()

        new_hash = self._password_service.hash(new_password)
        await self._user_repo.update_password_hash(row.user_id, new_hash)
        await self._password_reset_repo.mark_used(row.id)
        # Per invariant 8: revoke every active session for the user
        await self._session_repo.revoke_all_for_user(row.user_id)
        completed_at = datetime.now(UTC)
        await events.emit_password_reset_completed(
            user_id=row.user_id,
            reset_chain_id=row.reset_chain_id,
            completed_at=completed_at,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=row.user_id,
            action="iam.user.password_reset",
            resource_type="user",
            resource_id=row.user_id,
            payload=None,
            session=self._session,
        )


__all__ = [
    "EMAIL_VERIFICATION_TTL_SECONDS",
    "PASSWORD_RESET_TTL_SECONDS",
    "AccountRecoveryService",
]
