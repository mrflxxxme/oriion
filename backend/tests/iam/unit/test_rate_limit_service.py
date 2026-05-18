"""Unit: RateLimitService — INCR+EXPIRE atomic + per-scope thresholds."""

from __future__ import annotations

import pytest
from src.iam.services.rate_limit_service import RateLimitService


@pytest.mark.asyncio
async def test_login_under_threshold_is_allowed(
    rate_limit_service: RateLimitService,
) -> None:
    for i in range(5):
        v = await rate_limit_service.check_and_increment(scope="login", ip="1.2.3.4", email="a@b.c")
        assert v.allowed is True, f"hit {i + 1} should be allowed"
        assert v.remaining >= 0


@pytest.mark.asyncio
async def test_login_6th_attempt_is_blocked_with_retry_after(
    rate_limit_service: RateLimitService,
) -> None:
    for _ in range(5):
        await rate_limit_service.check_and_increment(scope="login", ip="1.2.3.4", email="a@b.c")
    v = await rate_limit_service.check_and_increment(scope="login", ip="1.2.3.4", email="a@b.c")
    assert v.allowed is False
    assert v.retry_after > 0
    assert v.remaining == 0


@pytest.mark.asyncio
async def test_email_normalisation_unifies_counters(
    rate_limit_service: RateLimitService,
) -> None:
    await rate_limit_service.check_and_increment(scope="login", ip="1.1.1.1", email="User@X.dev")
    v = await rate_limit_service.check_and_increment(
        scope="login", ip="1.1.1.1", email="user@x.dev"
    )
    assert v.remaining == 3  # 2 hits combined → 5 - 2 = 3


@pytest.mark.asyncio
async def test_forgot_threshold_is_3(rate_limit_service: RateLimitService) -> None:
    for _ in range(3):
        v = await rate_limit_service.check_and_increment(
            scope="forgot", ip="9.9.9.9", email="user@x.dev"
        )
        assert v.allowed is True
    v = await rate_limit_service.check_and_increment(
        scope="forgot", ip="9.9.9.9", email="user@x.dev"
    )
    assert v.allowed is False


@pytest.mark.asyncio
async def test_refresh_ip_only_key(rate_limit_service: RateLimitService) -> None:
    v = await rate_limit_service.check_and_increment(scope="refresh", ip="2.2.2.2")
    assert v.allowed is True
    assert v.remaining == 29


@pytest.mark.asyncio
async def test_unknown_scope_raises(rate_limit_service: RateLimitService) -> None:
    with pytest.raises(ValueError):
        await rate_limit_service.check_and_increment(scope="bogus", ip="x")
