"""Unit: domain exception attributes (code / status_code / title / detail / retry_after)."""

from __future__ import annotations

from src.iam.exceptions import (
    ConsentMissing,
    EmailAlreadyRegistered,
    EmailNotVerified,
    IamError,
    InvalidCredentials,
    RateLimitExceeded,
    TokenExpired,
    TokenInvalid,
    TokenNotFound,
    TokenRevoked,
    TokenRotationError,
    UserNotFound,
    WeakPassword,
)


def test_iam_error_base_defaults() -> None:
    e = IamError("boom")
    assert e.code == "iam.error"
    assert e.status_code == 500
    assert e.detail == "boom"


def test_known_codes_and_statuses() -> None:
    assert InvalidCredentials().status_code == 401
    assert EmailAlreadyRegistered().status_code == 409
    assert ConsentMissing().status_code == 422
    assert TokenExpired().code == "iam.auth.token_expired"
    assert TokenInvalid().status_code == 401
    assert TokenRevoked().code == "iam.auth.token_revoked"
    assert TokenRotationError().status_code == 401
    assert TokenNotFound().status_code == 410
    assert EmailNotVerified().status_code == 403
    assert WeakPassword().status_code == 422
    assert UserNotFound().status_code == 404


def test_rate_limit_exceeded_carries_retry_after() -> None:
    e = RateLimitExceeded(retry_after=42, detail="too many")
    assert e.retry_after == 42
    assert e.detail == "too many"
    assert e.status_code == 429
