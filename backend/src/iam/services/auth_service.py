"""Auth orchestration — composes everything in iam.services + repositories.

Public methods:
    register                      — POST /auth/register
    login                         — POST /auth/login
    logout                        — POST /auth/logout
    rotate_refresh                — POST /auth/refresh
    verify_email                  — POST /auth/verify-email
    resend_verification           — POST /auth/resend-verification (anti-enum 202)
    forgot_password               — POST /auth/forgot-password     (anti-enum 202)
    reset_password                — POST /auth/reset-password

Phase 00.2.5: stubs deleted; emit_audit_event + provision_initial_workspace
now resolve to the real impls landed by Phase 00.3. The service holds an
AsyncSession so both calls can participate in the request's outer TX —
audit_log inserts and workspace+cell provisioning land atomically with the
user-row create instead of leaking on partial failure.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.db.rls import set_tenant_context
from src.agents.services.team_provisioning_service import TeamProvisioningService
from src.audit.services.audit_service import emit_audit_event
from src.iam import events
from src.iam.exceptions import (
    ConsentMissing,
    EmailAlreadyRegistered,
    EmailNotVerified,
    InvalidCredentials,
    RateLimitExceeded,
    TokenRotationError,
)
from src.iam.repositories.consent_repository import ConsentRepository
from src.iam.repositories.email_verification_repository import (
    EmailVerificationTokenRepository,
)
from src.iam.repositories.password_reset_repository import PasswordResetTokenRepository
from src.iam.repositories.refresh_token_repository import RefreshTokenRepository
from src.iam.repositories.session_repository import SessionRepository
from src.iam.repositories.user_repository import UserRepository
from src.iam.schemas import (
    LoginCommand,
    RegisterCommand,
    RegisterResult,
    TokenPair,
    UserResponse,
)
from src.iam.services.account_recovery_service import AccountRecoveryService
from src.iam.services.consent_service import ConsentService
from src.iam.services.email_service import EmailSender
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService
from src.iam.services.token_service import TokenService
from src.multitenancy.services.workspace_service import provision_initial_workspace

# Token TTL per contract README invariant 7 (used by register's inline
# email-verification token; the recovery-flow TTLs live in
# account_recovery_service.py).
EMAIL_VERIFICATION_TTL_SECONDS = 24 * 3600  # 24h


def _hash_token_plaintext(plaintext: str) -> str:
    import hashlib

    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _new_token_plaintext() -> str:
    return secrets.token_urlsafe(32)


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        refresh_repo: RefreshTokenRepository,
        consent_repo: ConsentRepository,
        email_verif_repo: EmailVerificationTokenRepository,
        password_reset_repo: PasswordResetTokenRepository,
        password_service: PasswordService,
        token_service: TokenService,
        rate_limit_service: RateLimitService,
        consent_service: ConsentService,
        email_sender: EmailSender,
        require_email_verification: bool,
        refresh_ttl_seconds: int,
        access_ttl_seconds: int,
        team_provisioning_service: TeamProvisioningService | None = None,
    ) -> None:
        # Session is passed in so audit_log inserts + provision_initial_workspace
        # share the request's outer TX with the user / refresh-token writes.
        self._session = session
        # Phase 00.5b Commit 5: optional injection. Production wiring in
        # iam/deps.py supplies the real TeamProvisioningService so register()
        # auto-spawns productivity-core team (AC1). Unit tests pass None to
        # skip the cross-context call.
        self._team_provisioning_service = team_provisioning_service
        self._user_repo = user_repo
        self._session_repo = session_repo
        self._refresh_repo = refresh_repo
        self._consent_repo = consent_repo
        self._email_verif_repo = email_verif_repo
        self._password_reset_repo = password_reset_repo
        self._password_service = password_service
        self._token_service = token_service
        self._rate_limit_service = rate_limit_service
        self._consent_service = consent_service
        self._email_sender = email_sender
        self._require_email_verification = require_email_verification
        self._refresh_ttl_seconds = refresh_ttl_seconds
        self._access_ttl_seconds = access_ttl_seconds
        # Account-recovery flows (email-verification + password-reset) live in a
        # focused collaborator (file-size canon split). AuthService stays a
        # facade: the four recovery methods below delegate here, sharing the
        # request's session so audit inserts keep landing in the outer TX.
        self._account_recovery = AccountRecoveryService(
            session=session,
            user_repo=user_repo,
            session_repo=session_repo,
            email_verif_repo=email_verif_repo,
            password_reset_repo=password_reset_repo,
            password_service=password_service,
            rate_limit_service=rate_limit_service,
            email_sender=email_sender,
        )

    # ── register ────────────────────────────────────────────────────────

    async def register(self, cmd: RegisterCommand) -> RegisterResult:
        if not cmd.consent_pdn:
            raise ConsentMissing()

        # Rate-limit per (ip, email)
        if cmd.ip:
            verdict = await self._rate_limit_service.check_and_increment(
                scope="register", ip=cmd.ip, email=cmd.email
            )
            if not verdict.allowed:
                raise RateLimitExceeded(retry_after=verdict.retry_after)

        if await self._user_repo.find_by_email(cmd.email):
            raise EmailAlreadyRegistered()

        password_hash = self._password_service.hash(cmd.password)
        user = await self._user_repo.create(
            email=cmd.email,
            password_hash=password_hash,
            display_name=cmd.display_name,
            locale=cmd.locale,
        )

        # FZ-152 consent recording
        await self._consent_service.record(
            user_id=user.id, kind="pdn", ip=cmd.ip, user_agent=cmd.user_agent
        )
        if cmd.consent_marketing:
            await self._consent_service.record(
                user_id=user.id,
                kind="marketing",
                ip=cmd.ip,
                user_agent=cmd.user_agent,
            )

        # Provision first workspace + initial cell. Real impl is idempotent
        # on workspace slug (see workspace_service.py:166-179) — slug is
        # derived from the email localpart. Naive split is acceptable for
        # Wave 0 (1 user -> 1 workspace at registration; collision between
        # alice@x and alice@y is a known Wave-1 user-testing risk).
        provision = await provision_initial_workspace(
            session=self._session,
            user_id=user.id,
            email_localpart=cmd.email.split("@", 1)[0],
        )

        # Phase 00.5b Commit 5 AC1 / Phase 00.6 Commit 3 hygiene refactor:
        # spawn the productivity-core team automatically when the user's
        # first cell is provisioned. The 3-GUC tenant context must be set
        # before the FORCE-RLS-protected agent_instances INSERT passes WITH
        # CHECK under oriion_app. We delegate to the canonical async-cm
        # `set_tenant_context` helper from `_shared/db/rls.py` instead of
        # repeating inline `SELECT set_config()` plumbing (closes F-CR-M2 +
        # F-ARC-M4 from Phase 00.5b audit). GUCs auto-reset at TX end so no
        # state leaks across requests; SAME-TX semantics preserved — a
        # failed team provisioning rolls back the workspace. Skipped when
        # team_provisioning_service is None (unit-test mode); production
        # wiring in iam/deps.py always supplies it.
        if self._team_provisioning_service is not None:
            async with set_tenant_context(
                self._session,
                workspace_id=provision.workspace_id,
                cell_id=provision.cell_id,
                user_id=user.id,
            ):
                await self._team_provisioning_service.provision_team(
                    preset_slug="productivity-core",
                    cell_id=provision.cell_id,
                    user_id=user.id,
                )

        # Issue email-verification token
        plaintext = _new_token_plaintext()
        token_hash = _hash_token_plaintext(plaintext)
        expires_at = datetime.now(UTC) + timedelta(seconds=EMAIL_VERIFICATION_TTL_SECONDS)
        verif_row = await self._email_verif_repo.create(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )
        await self._email_sender.send_verification_email(
            to=user.email, token=plaintext, expires_at=expires_at
        )

        # Audit + CloudEvents
        registered_at = user.created_at or datetime.now(UTC)
        await events.emit_user_registered(
            user_id=user.id, email=user.email, registered_at=registered_at
        )
        await events.emit_email_verification_requested(
            user_id=user.id,
            email=user.email,
            token_id=verif_row.id,
            expires_at=expires_at,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=user.id,
            action="iam.user.registered",
            resource_type="user",
            resource_id=user.id,
            payload={"email": user.email, "workspace_id": str(provision.workspace_id)},
            ip=cmd.ip,
            user_agent=cmd.user_agent,
            session=self._session,
            workspace_id=provision.workspace_id,
            cell_id=provision.cell_id,
        )

        return RegisterResult(
            user_id=user.id,
            workspace_id=provision.workspace_id,
            cell_id=provision.cell_id,
            email=user.email,
            email_verification_sent=True,
        )

    # ── login ───────────────────────────────────────────────────────────

    async def login(self, cmd: LoginCommand) -> TokenPair:
        if cmd.ip:
            verdict = await self._rate_limit_service.check_and_increment(
                scope="login", ip=cmd.ip, email=cmd.email
            )
            if not verdict.allowed:
                raise RateLimitExceeded(retry_after=verdict.retry_after)

        user = await self._user_repo.find_by_email(cmd.email)
        if user is None or user.password_hash is None:
            raise InvalidCredentials()

        if not self._password_service.verify(user.password_hash, cmd.password):
            raise InvalidCredentials()

        if self._require_email_verification and user.email_verified_at is None:
            raise EmailNotVerified()

        return await self._issue_token_pair(user_id=user.id, ip=cmd.ip, user_agent=cmd.user_agent)

    async def _issue_token_pair(
        self,
        *,
        user_id: UUID,
        ip: str | None,
        user_agent: str | None,
        rotation_chain_id: UUID | None = None,
    ) -> TokenPair:
        session = await self._session_repo.create(
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            ttl_seconds=self._refresh_ttl_seconds,
        )
        access = self._token_service.issue_access_token(user_id=user_id, session_id=session.id)
        refresh = self._token_service.generate_refresh_token()
        chain_id = rotation_chain_id or uuid4()
        await self._refresh_repo.create(
            session_id=session.id,
            token_hash=refresh.token_hash,
            rotation_chain_id=chain_id,
            expires_at=refresh.expires_at,
        )
        await events.emit_session_created(
            session_id=session.id,
            user_id=user_id,
            expires_at=session.expires_at,
            ip=ip,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=user_id,
            action="iam.auth.login",
            resource_type="session",
            resource_id=session.id,
            payload=None,
            ip=ip,
            user_agent=user_agent,
            session=self._session,
        )
        return TokenPair(
            access_token=access.token,
            refresh_token=refresh.plaintext,
            expires_in=access.expires_in,
        )

    # ── logout ──────────────────────────────────────────────────────────

    async def logout(
        self,
        refresh_token: str,
        access_jti: UUID | None = None,
        access_remaining_ttl: int | None = None,
    ) -> None:
        token_hash = self._token_service.hash_refresh_token(refresh_token)
        row = await self._refresh_repo.find_by_hash(token_hash)
        if row is None:
            return  # logout is idempotent

        # Look up the session BEFORE revoke so we can attribute the audit
        # row to the real user_id (was UUID(int=0) pre-Phase-00.2.5 — see
        # audit M-1 finding). Refresh-token is unauthenticated by design,
        # but the refresh-token row carries session_id → session.user_id.
        session_row = await self._session_repo.find_by_id(row.session_id)
        actor_id_for_audit = session_row.user_id if session_row is not None else UUID(int=0)

        await self._session_repo.revoke(row.session_id)
        await self._refresh_repo.revoke_chain(row.rotation_chain_id)
        if access_jti is not None and access_remaining_ttl is not None:
            await self._token_service.blacklist_jti(access_jti, access_remaining_ttl)
        await events.emit_session_revoked(session_id=row.session_id, reason="user_action")
        await emit_audit_event(
            actor_type="user",
            actor_id=actor_id_for_audit,
            action="iam.auth.logout",
            resource_type="session",
            resource_id=row.session_id,
            payload=None,
            session=self._session,
        )

    # ── rotate_refresh (OWASP chain-revoke) ─────────────────────────────

    async def rotate_refresh(
        self, refresh_token: str, *, ip: str | None, user_agent: str | None
    ) -> TokenPair:
        if ip:
            verdict = await self._rate_limit_service.check_and_increment(scope="refresh", ip=ip)
            if not verdict.allowed:
                raise RateLimitExceeded(retry_after=verdict.retry_after)

        token_hash = self._token_service.hash_refresh_token(refresh_token)
        old = await self._refresh_repo.find_by_hash(token_hash)
        if old is None:
            raise TokenRotationError("refresh token not found")

        # Reuse detection: a token presented twice → chain-revoke entire branch
        if old.used_at is not None or old.revoked_at is not None:
            await self._refresh_repo.revoke_chain(old.rotation_chain_id)
            await self._session_repo.revoke(old.session_id)
            await events.emit_session_revoked(session_id=old.session_id, reason="security_incident")
            await emit_audit_event(
                actor_type="system",
                actor_id=UUID(int=0),
                action="iam.auth.refresh_reuse_detected",
                resource_type="session",
                resource_id=old.session_id,
                payload={"rotation_chain_id": str(old.rotation_chain_id)},
                ip=ip,
                user_agent=user_agent,
                session=self._session,
            )
            raise TokenRotationError("refresh token already used — chain revoked")

        session = await self._session_repo.find_by_id(old.session_id)
        if session is None or session.revoked_at is not None:
            raise TokenRotationError("session revoked")

        # Issue replacement pair on the same rotation_chain_id
        access = self._token_service.issue_access_token(
            user_id=session.user_id, session_id=session.id
        )
        new_refresh = self._token_service.generate_refresh_token()
        new_row = await self._refresh_repo.create(
            session_id=session.id,
            token_hash=new_refresh.token_hash,
            rotation_chain_id=old.rotation_chain_id,
            expires_at=new_refresh.expires_at,
        )
        await self._refresh_repo.mark_used_and_link(old.id, new_row.id)
        await events.emit_refresh_rotated(
            old_token_id=old.id,
            new_token_id=new_row.id,
            rotation_chain_id=old.rotation_chain_id,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=session.user_id,
            action="iam.auth.refresh",
            resource_type="session",
            resource_id=session.id,
            payload=None,
            ip=ip,
            user_agent=user_agent,
            session=self._session,
        )
        return TokenPair(
            access_token=access.token,
            refresh_token=new_refresh.plaintext,
            expires_in=access.expires_in,
        )

    # ── account-recovery (delegated to AccountRecoveryService) ──────────
    # Facade delegators preserve the public AuthService surface (routers +
    # tests keep calling these on the auth service); the flows themselves
    # live in ``account_recovery_service.py``.

    async def verify_email(self, plaintext_token: str) -> None:
        await self._account_recovery.verify_email(plaintext_token)

    async def resend_verification(
        self, email: str, *, ip: str | None, user_agent: str | None
    ) -> None:
        await self._account_recovery.resend_verification(email, ip=ip, user_agent=user_agent)

    async def forgot_password(self, email: str, *, ip: str | None, user_agent: str | None) -> None:
        await self._account_recovery.forgot_password(email, ip=ip, user_agent=user_agent)

    async def reset_password(self, plaintext_token: str, new_password: str) -> None:
        await self._account_recovery.reset_password(plaintext_token, new_password)

    # ── /users/me helpers (kept here so router stays thin) ──────────────

    async def get_user_profile(self, user_id: UUID) -> UserResponse:
        user = await self._user_repo.find_by_id(user_id)
        if user is None:
            raise InvalidCredentials()
        return UserResponse.model_validate(user)

    async def update_user_profile(
        self,
        user_id: UUID,
        *,
        display_name: str | None = None,
        locale: str | None = None,
        timezone: str | None = None,
    ) -> UserResponse:
        await self._user_repo.update_profile(
            user_id,
            display_name=display_name,
            locale=locale,
            timezone=timezone,
        )
        return await self.get_user_profile(user_id)
