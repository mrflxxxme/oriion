"""Unit: TokenService — JWT issue/verify, blacklist, refresh hashing."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from src._shared.config import Settings
from src.iam.exceptions import TokenExpired, TokenInvalid, TokenRevoked
from src.iam.services.token_service import TokenService


@pytest.mark.asyncio
async def test_issue_and_verify_access_token_roundtrip(
    token_service: TokenService,
) -> None:
    user_id, sid = uuid4(), uuid4()
    issued = token_service.issue_access_token(user_id=user_id, session_id=sid)
    assert issued.expires_in == 900

    claims = await token_service.verify_access_token(issued.token)
    assert claims.sub == user_id
    assert claims.sid == sid
    assert claims.jti == issued.jti
    assert claims.iss == "oriion-iam"
    assert claims.aud == "oriion-app"
    assert claims.type == "access"


@pytest.mark.asyncio
async def test_verify_expired_token_raises_token_expired(
    settings: Settings, token_service: TokenService
) -> None:
    user_id, sid = uuid4(), uuid4()
    payload = {
        "sub": str(user_id),
        "sid": str(sid),
        "jti": str(uuid4()),
        "iat": int(time.time()) - 1000,
        "exp": int(time.time()) - 500,
        "iss": settings.jwt_iss,
        "aud": settings.jwt_aud,
        "type": "access",
    }
    expired = jwt.encode(
        payload, settings.jwt_secret_access_v1.get_secret_value(), algorithm="HS256"
    )
    with pytest.raises(TokenExpired):
        await token_service.verify_access_token(expired)


@pytest.mark.asyncio
async def test_verify_wrong_signature_raises_token_invalid(
    token_service: TokenService,
) -> None:
    bad = jwt.encode({"sub": "x"}, "different-secret", algorithm="HS256")
    with pytest.raises(TokenInvalid):
        await token_service.verify_access_token(bad)


@pytest.mark.asyncio
async def test_verify_wrong_audience_raises_token_invalid(
    settings: Settings, token_service: TokenService
) -> None:
    payload = {
        "sub": str(uuid4()),
        "sid": str(uuid4()),
        "jti": str(uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "iss": settings.jwt_iss,
        "aud": "other-aud",
        "type": "access",
    }
    tok = jwt.encode(payload, settings.jwt_secret_access_v1.get_secret_value(), algorithm="HS256")
    with pytest.raises(TokenInvalid):
        await token_service.verify_access_token(tok)


@pytest.mark.asyncio
async def test_blacklist_and_verify_raises_token_revoked(
    token_service: TokenService,
) -> None:
    issued = token_service.issue_access_token(user_id=uuid4(), session_id=uuid4())
    await token_service.blacklist_jti(issued.jti, remaining_ttl_seconds=600)
    with pytest.raises(TokenRevoked):
        await token_service.verify_access_token(issued.token)


@pytest.mark.asyncio
async def test_blacklist_zero_ttl_is_noop(token_service: TokenService) -> None:
    issued = token_service.issue_access_token(user_id=uuid4(), session_id=uuid4())
    await token_service.blacklist_jti(issued.jti, remaining_ttl_seconds=0)
    # Not blacklisted — verify succeeds
    claims = await token_service.verify_access_token(issued.token)
    assert claims.jti == issued.jti


def test_generate_refresh_token_entropy_and_hash(
    token_service: TokenService,
) -> None:
    a = token_service.generate_refresh_token()
    b = token_service.generate_refresh_token()
    assert a.plaintext != b.plaintext
    assert len(a.plaintext) >= 32
    assert len(a.token_hash) == 64  # sha256 hex
    assert a.token_hash == token_service.hash_refresh_token(a.plaintext)
    # Refresh TTL set per settings (7 days)
    now = datetime.now(UTC)
    assert a.expires_at - now > timedelta(days=6)
