"""Magic-link (passwordless) login — request + consume (Phase 01.8).

Built on the existing ``EmailSender`` port (InMemory in tests). Mirrors the
account-recovery token idiom: a single-use token, SHA-256 hashed at rest, short
TTL, plaintext only over email. Consuming a valid token issues a session +
token-pair exactly like password login — via an injected ``issue_token_pair``
callback so the token-issuance path stays single-sourced in ``AuthService``.

Anti-enumeration: /request always returns 202 regardless of whether the email
exists, and never reveals existence through timing-visible branches beyond the
existing recovery flows.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.services.audit_service import emit_audit_event
from src.iam.exceptions import RateLimitExceeded, TokenNotFound
from src.iam.repositories.magic_link_repository import MagicLinkTokenRepository
from src.iam.repositories.user_repository import UserRepository
from src.iam.schemas import TokenPair
from src.iam.services.email_service import EmailSender
from src.iam.services.rate_limit_service import RateLimitService

# Short TTL — a login link should not linger. 15 min balances email-delivery
# latency against replay window.
MAGIC_LINK_TTL_SECONDS = 15 * 60

IssueTokenPair = Callable[..., Awaitable[TokenPair]]


def _hash_token_plaintext(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _new_token_plaintext() -> str:
    return secrets.token_urlsafe(32)


class MagicLinkService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        user_repo: UserRepository,
        magic_link_repo: MagicLinkTokenRepository,
        rate_limit_service: RateLimitService,
        email_sender: EmailSender,
        issue_token_pair: IssueTokenPair,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._magic_link_repo = magic_link_repo
        self._rate_limit_service = rate_limit_service
        self._email_sender = email_sender
        self._issue_token_pair = issue_token_pair

    # ── request (anti-enum 202) ─────────────────────────────────────────

    async def request(self, email: str, *, ip: str | None, user_agent: str | None) -> None:
        if ip:
            verdict = await self._rate_limit_service.check_and_increment(
                scope="magic_link", ip=ip, email=email
            )
            if not verdict.allowed:
                raise RateLimitExceeded(retry_after=verdict.retry_after)

        user = await self._user_repo.find_by_email(email)
        if user is None:
            return  # anti-enum: do not signal existence

        await self._magic_link_repo.revoke_unused_for_user(user.id)
        plaintext = _new_token_plaintext()
        expires_at = datetime.now(UTC) + timedelta(seconds=MAGIC_LINK_TTL_SECONDS)
        await self._magic_link_repo.create(
            user_id=user.id,
            token_hash=_hash_token_plaintext(plaintext),
            expires_at=expires_at,
        )
        await self._email_sender.send_magic_link_email(
            to=user.email, token=plaintext, expires_at=expires_at
        )

    # ── consume (issues a token pair) ───────────────────────────────────

    async def consume(
        self, plaintext_token: str, *, ip: str | None, user_agent: str | None
    ) -> TokenPair:
        token_hash = _hash_token_plaintext(plaintext_token)
        row = await self._magic_link_repo.find_active_by_hash(token_hash)
        if row is None or row.expires_at < datetime.now(UTC):
            raise TokenNotFound()

        # Single-use: consume BEFORE issuing so a replay in a race still can't
        # mint a second session (mark_used flips used_at; find_active filters it).
        await self._magic_link_repo.mark_used(row.id)

        user_id: UUID = row.user_id
        await emit_audit_event(
            actor_type="user",
            actor_id=user_id,
            action="iam.auth.magic_link_login",
            resource_type="user",
            resource_id=user_id,
            payload=None,
            ip=ip,
            user_agent=user_agent,
            session=self._session,
        )
        return await self._issue_token_pair(user_id=user_id, ip=ip, user_agent=user_agent)
