"""JWT access token + opaque refresh token + Redis blacklist.

Access tokens: HS256 JWT with claims sub/sid/jti/iat/exp/iss/aud/type.
Refresh tokens: opaque random 256-bit (secrets.token_urlsafe(32)),
                stored as SHA-256 hex hash. NOT a JWT.

Blacklist: on logout we SET blacklist:jwt:{jti} 1 EX <remaining_ttl>.
verify_access_token checks blacklist on every call → 401 TokenRevoked.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from redis.asyncio import Redis

from src._shared.config import Settings
from src.iam.exceptions import (
    TokenExpired,
    TokenInvalid,
    TokenRevoked,
    TotpChallengeInvalid,
)
from src.iam.schemas import AccessTokenClaims

BLACKLIST_PREFIX = "blacklist:jwt:"

# The login-time 2FA challenge is a short-lived signed token that binds a
# verified password to the pending TOTP step. 5 min is ample for a user to
# fetch a code from their authenticator without leaving a broad replay window.
TOTP_CHALLENGE_TTL_SECONDS = 300


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    """Output of issue_access_token — keeps jti + exp for blacklist accounting."""

    token: str
    jti: UUID
    expires_at: datetime
    expires_in: int  # seconds until exp


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    """Output of generate_refresh_token — token + SHA-256 hex hash for storage."""

    plaintext: str
    token_hash: str
    expires_at: datetime


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TokenService:
    """Issue + verify + blacklist JWT and opaque refresh tokens."""

    def __init__(self, settings: Settings, redis: Redis) -> None:
        self._settings = settings
        self._redis = redis

    # ── access token (JWT HS256) ────────────────────────────────────────

    def issue_access_token(self, user_id: UUID, session_id: UUID) -> IssuedAccessToken:
        now = datetime.now(UTC)
        ttl = self._settings.jwt_access_ttl_seconds
        exp_dt = now + timedelta(seconds=ttl)
        jti = uuid4()

        payload = {
            "sub": str(user_id),
            "sid": str(session_id),
            "jti": str(jti),
            "iat": int(now.timestamp()),
            "exp": int(exp_dt.timestamp()),
            "iss": self._settings.jwt_iss,
            "aud": self._settings.jwt_aud,
            "type": "access",
        }
        token = jwt.encode(
            payload,
            self._settings.jwt_secret_access_v1.get_secret_value(),
            algorithm="HS256",
        )
        return IssuedAccessToken(token=token, jti=jti, expires_at=exp_dt, expires_in=ttl)

    async def verify_access_token(self, token: str) -> AccessTokenClaims:
        """Decode + validate JWT and Redis blacklist.

        Raises TokenExpired / TokenInvalid / TokenRevoked.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_access_v1.get_secret_value(),
                algorithms=["HS256"],
                audience=self._settings.jwt_aud,
                issuer=self._settings.jwt_iss,
                options={"require": ["exp", "iat", "sub", "sid", "jti", "type"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpired() from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalid(str(exc)) from exc

        if payload.get("type") != "access":
            raise TokenInvalid("type mismatch")

        try:
            claims = AccessTokenClaims(**payload)
        except Exception as exc:
            raise TokenInvalid(f"claims malformed: {exc}") from exc

        if await self._is_blacklisted(claims.jti):
            raise TokenRevoked()

        return claims

    async def blacklist_jti(self, jti: UUID, remaining_ttl_seconds: int) -> None:
        """Mark a jti as revoked until its natural expiry.

        EX matches remaining TTL so Redis auto-cleans expired entries.
        """
        if remaining_ttl_seconds <= 0:
            return
        await self._redis.set(
            name=f"{BLACKLIST_PREFIX}{jti}",
            value="1",
            ex=remaining_ttl_seconds,
        )

    async def _is_blacklisted(self, jti: UUID) -> bool:
        return bool(await self._redis.exists(f"{BLACKLIST_PREFIX}{jti}"))

    # ── refresh token (opaque + SHA-256 hash storage) ───────────────────

    def generate_refresh_token(self) -> IssuedRefreshToken:
        plaintext = secrets.token_urlsafe(32)  # 256-bit entropy → 43-char b64url
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._settings.refresh_ttl_seconds)
        return IssuedRefreshToken(
            plaintext=plaintext,
            token_hash=_sha256_hex(plaintext),
            expires_at=expires_at,
        )

    def hash_refresh_token(self, plaintext: str) -> str:
        """Compute the storage hash for a presented refresh token."""
        return _sha256_hex(plaintext)

    # ── 2FA challenge token (short-lived HS256, Phase 01.8) ──────────────

    def issue_totp_challenge(self, user_id: UUID) -> str:
        """Signed, 5-min token issued after a correct password when 2FA is on.

        Self-contained (no DB/Redis): the signature + short exp make it
        un-forgeable and un-replayable past its window. type='totp_challenge'
        so it can NEVER be confused with an access token by verify_access_token.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "jti": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=TOTP_CHALLENGE_TTL_SECONDS)).timestamp()),
            "iss": self._settings.jwt_iss,
            "aud": self._settings.jwt_aud,
            "type": "totp_challenge",
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_access_v1.get_secret_value(),
            algorithm="HS256",
        )

    def verify_totp_challenge(self, token: str) -> UUID:
        """Return the user_id bound to a valid challenge token, else raise.

        Raises TotpChallengeInvalid on any tamper / expiry / type mismatch —
        never leaks whether the failure was expiry vs signature vs type.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_access_v1.get_secret_value(),
                algorithms=["HS256"],
                audience=self._settings.jwt_aud,
                issuer=self._settings.jwt_iss,
                options={"require": ["exp", "iat", "sub", "jti", "type"]},
            )
        except jwt.InvalidTokenError as exc:
            raise TotpChallengeInvalid(str(exc)) from exc
        if payload.get("type") != "totp_challenge":
            raise TotpChallengeInvalid("type mismatch")
        try:
            return UUID(str(payload["sub"]))
        except (KeyError, ValueError) as exc:
            raise TotpChallengeInvalid("sub malformed") from exc
