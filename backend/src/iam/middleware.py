"""FastAPI dependency: get_current_user (Bearer JWT).

Reads Authorization header, verifies + decodes JWT via TokenService, loads
the User row from DB. 401 on missing/invalid/expired/revoked token.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.config import Settings, get_settings
from src._shared.db.redis import get_redis
from src._shared.db.session import get_db
from src.iam.exceptions import TokenInvalid
from src.iam.models import User
from src.iam.repositories.user_repository import UserRepository
from src.iam.schemas import AccessTokenClaims
from src.iam.services.token_service import TokenService


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Tuple of the verified claims and the freshly-loaded User row."""

    claims: AccessTokenClaims
    user: User


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise TokenInvalid("missing Authorization header")
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise TokenInvalid("malformed Authorization header (expected 'Bearer <jwt>')")
    return parts[1]


def get_token_service(
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis),
) -> TokenService:
    return TokenService(settings=settings, redis=redis)


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> AuthenticatedUser:
    bearer = _extract_bearer(authorization)
    claims = await token_service.verify_access_token(bearer)
    user = await UserRepository(db).find_by_id(claims.sub)
    if user is None or user.deleted_at is not None:
        raise TokenInvalid("user not found or deleted")
    return AuthenticatedUser(claims=claims, user=user)


# Convenience for routers that only need the user_id
async def get_current_user_id(
    auth: AuthenticatedUser = Depends(get_current_user),
) -> UUID:
    return auth.user.id
