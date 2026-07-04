"""FastAPI dependency factories for iam services.

Each Depends() returns a fresh instance scoped to the request. The
shared singletons (Settings, Redis client) are cached at the module
level so we don't allocate them per-request.
"""

from __future__ import annotations

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.config import Settings, get_settings
from src._shared.db.redis import get_redis
from src._shared.db.session import get_db
from src.agents.services.team_provisioning_service import TeamProvisioningService
from src.billing.services.subscription_service import TrialProvisioningService
from src.iam.middleware import get_token_service
from src.iam.repositories.consent_repository import ConsentRepository
from src.iam.repositories.email_verification_repository import (
    EmailVerificationTokenRepository,
)
from src.iam.repositories.magic_link_repository import MagicLinkTokenRepository
from src.iam.repositories.password_reset_repository import PasswordResetTokenRepository
from src.iam.repositories.refresh_token_repository import RefreshTokenRepository
from src.iam.repositories.session_repository import SessionRepository
from src.iam.repositories.totp_repository import (
    TotpBackupCodeRepository,
    TotpCredentialRepository,
)
from src.iam.repositories.user_repository import UserRepository
from src.iam.services.auth_service import AuthService
from src.iam.services.consent_service import ConsentService
from src.iam.services.email_service import (
    ConsoleEmailSender,
    EmailSender,
    NoOpEmailSender,
    YandexSmtpEmailSender,
)
from src.iam.services.magic_link_service import MagicLinkService
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService
from src.iam.services.token_service import TokenService
from src.iam.services.totp_service import TotpService
from src.llm_gateway.services.kms_provider import (
    KMSProvider,
    LocalAESKMS,
    YandexKMS,
)


def get_password_service() -> PasswordService:
    return PasswordService()


def get_rate_limit_service(redis: Redis = Depends(get_redis)) -> RateLimitService:
    return RateLimitService(redis=redis)


def get_email_sender(settings: Settings = Depends(get_settings)) -> EmailSender:
    """Select the outbound email sender (Phase 01.8).

    * dev / test → ConsoleEmailSender (token to structured log).
    * prod/staging WITH SMTP creds → YandexSmtpEmailSender (real send).
    * prod/staging WITHOUT SMTP creds → NoOpEmailSender fallback, so a
      credential-less boot does NOT crash and the deferred-live-send contract
      (ADR-007) holds until creds land in the canonical .env / Lockbox.
    """
    if settings.is_dev or settings.is_test:
        return ConsoleEmailSender()
    if settings.is_smtp_configured:
        return YandexSmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password.get_secret_value(),
            sender=settings.smtp_sender_address,
            use_tls=settings.smtp_use_tls,
            timeout=settings.smtp_timeout_seconds,
            url_base=settings.email_verify_url_base,
        )
    return NoOpEmailSender()


def get_consent_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConsentService:
    return ConsentService(
        consent_repo=ConsentRepository(db),
        consent_version=settings.consent_version_current,
        session=db,
    )


def get_iam_kms_provider(settings: Settings = Depends(get_settings)) -> KMSProvider:
    """Build the KMS provider for iam at-rest encryption FROM SETTINGS.

    Deliberately Settings-driven (not the llm_gateway app.state provider) so
    the iam auth surface has NO dependency on the llm_gateway lifespan startup —
    an app that mounts only the iam routers (or a test that overrides only iam
    deps) still resolves a working KMS. Uses the same construction as the
    canonical secret-refresh path (``_shared.secret_refresh``): 'local' →
    LocalAESKMS(master_key from Settings), 'yandex' → YandexKMS.
    """
    from src._shared.secret_refresh import resolve_master_key_bytes

    if settings.kms_backend == "yandex":
        return YandexKMS()
    return LocalAESKMS(master_key=resolve_master_key_bytes(settings))


def get_totp_service(
    db: AsyncSession = Depends(get_db),
    kms: KMSProvider = Depends(get_iam_kms_provider),
) -> TotpService:
    return TotpService(
        credential_repo=TotpCredentialRepository(db),
        backup_code_repo=TotpBackupCodeRepository(db),
        user_repo=UserRepository(db),
        kms=kms,
    )


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    token_service: TokenService = Depends(get_token_service),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    email_sender: EmailSender = Depends(get_email_sender),
    consent_service: ConsentService = Depends(get_consent_service),
    password_service: PasswordService = Depends(get_password_service),
    totp_service: TotpService = Depends(get_totp_service),
) -> AuthService:
    return AuthService(
        session=db,
        user_repo=UserRepository(db),
        session_repo=SessionRepository(db),
        refresh_repo=RefreshTokenRepository(db),
        consent_repo=ConsentRepository(db),
        email_verif_repo=EmailVerificationTokenRepository(db),
        password_reset_repo=PasswordResetTokenRepository(db),
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        consent_service=consent_service,
        email_sender=email_sender,
        require_email_verification=settings.require_email_verification,
        refresh_ttl_seconds=settings.refresh_ttl_seconds,
        access_ttl_seconds=settings.jwt_access_ttl_seconds,
        team_provisioning_service=TeamProvisioningService(db),
        trial_provisioning_service=TrialProvisioningService(db),
        totp_service=totp_service,
    )


def get_magic_link_service(
    db: AsyncSession = Depends(get_db),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    email_sender: EmailSender = Depends(get_email_sender),
    auth_service: AuthService = Depends(get_auth_service),
) -> MagicLinkService:
    # The token-issuance path is single-sourced in AuthService; MagicLinkService
    # calls its (private-by-convention) _issue_token_pair so a magic-link login
    # mints exactly the same session + refresh chain + audit trail as password
    # login, without duplicating that logic.
    return MagicLinkService(
        session=db,
        user_repo=UserRepository(db),
        magic_link_repo=MagicLinkTokenRepository(db),
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        issue_token_pair=auth_service.issue_token_pair,
    )
