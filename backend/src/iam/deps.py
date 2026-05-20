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
from src.iam.middleware import get_token_service
from src.iam.repositories.consent_repository import ConsentRepository
from src.iam.repositories.email_verification_repository import (
    EmailVerificationTokenRepository,
)
from src.iam.repositories.password_reset_repository import PasswordResetTokenRepository
from src.iam.repositories.refresh_token_repository import RefreshTokenRepository
from src.iam.repositories.session_repository import SessionRepository
from src.iam.repositories.user_repository import UserRepository
from src.iam.services.auth_service import AuthService
from src.iam.services.consent_service import ConsentService
from src.iam.services.email_service import ConsoleEmailSender, EmailSender, NoOpEmailSender
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService
from src.iam.services.token_service import TokenService


def get_password_service() -> PasswordService:
    return PasswordService()


def get_rate_limit_service(redis: Redis = Depends(get_redis)) -> RateLimitService:
    return RateLimitService(redis=redis)


def get_email_sender(settings: Settings = Depends(get_settings)) -> EmailSender:
    if settings.is_dev or settings.is_test:
        return ConsoleEmailSender()
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


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    token_service: TokenService = Depends(get_token_service),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    email_sender: EmailSender = Depends(get_email_sender),
    consent_service: ConsentService = Depends(get_consent_service),
    password_service: PasswordService = Depends(get_password_service),
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
    )
