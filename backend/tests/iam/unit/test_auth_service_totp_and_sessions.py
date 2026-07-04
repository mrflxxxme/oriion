"""Unit: AuthService 2FA login gate + session-list/revoke authz (Phase 01.8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src._shared.config import Settings
from src.iam.exceptions import TotpInvalidCode, UserNotFound
from src.iam.schemas import LoginCommand, TokenPair, TotpChallenge
from src.iam.services.auth_service import AuthService
from src.iam.services.consent_service import ConsentService
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService
from src.iam.services.token_service import TokenService


def _make_user(*, password_hash: str, user_id=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id or uuid4(),
        email="user@x.dev",
        password_hash=password_hash,
        email_verified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        deleted_at=None,
    )


def _build(
    *,
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    user_repo: AsyncMock,
    session_repo: AsyncMock | None = None,
    refresh_repo: AsyncMock | None = None,
    totp_service: AsyncMock | None = None,
) -> AuthService:
    db_session = AsyncMock()
    return AuthService(
        session=db_session,
        user_repo=user_repo,
        session_repo=session_repo or AsyncMock(),
        refresh_repo=refresh_repo or AsyncMock(),
        consent_repo=AsyncMock(),
        email_verif_repo=AsyncMock(),
        password_reset_repo=AsyncMock(),
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        consent_service=ConsentService(
            AsyncMock(), settings.consent_version_current, session=db_session
        ),
        email_sender=AsyncMock(),
        require_email_verification=False,
        refresh_ttl_seconds=settings.refresh_ttl_seconds,
        access_ttl_seconds=settings.jwt_access_ttl_seconds,
        totp_service=totp_service,
    )


# ── login second-factor gate ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_without_2fa_returns_token_pair(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    pw = "very-strong-password-123"
    user = _make_user(password_hash=password_service.hash(pw))
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    session_repo = AsyncMock()
    session_repo.create.return_value = SimpleNamespace(
        id=uuid4(), expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    totp = AsyncMock()
    totp.is_enabled.return_value = False

    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=user_repo,
        session_repo=session_repo,
        totp_service=totp,
    )
    result = await svc.login(LoginCommand(email=user.email, password=pw))
    assert isinstance(result, TokenPair)


@pytest.mark.asyncio
async def test_login_with_active_2fa_returns_challenge_not_tokens(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    pw = "very-strong-password-123"
    user = _make_user(password_hash=password_service.hash(pw))
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    session_repo = AsyncMock()
    totp = AsyncMock()
    totp.is_enabled.return_value = True

    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=user_repo,
        session_repo=session_repo,
        totp_service=totp,
    )
    result = await svc.login(LoginCommand(email=user.email, password=pw))
    assert isinstance(result, TotpChallenge)
    assert result.two_factor_required is True
    # Crucially, NO session was minted on the password-only leg.
    session_repo.create.assert_not_awaited()
    # The challenge token round-trips back to the same user.
    assert token_service.verify_totp_challenge(result.challenge_token) == user.id


@pytest.mark.asyncio
async def test_login_totp_valid_code_issues_tokens(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    user_id = uuid4()
    user_repo = AsyncMock()
    session_repo = AsyncMock()
    session_repo.create.return_value = SimpleNamespace(
        id=uuid4(), expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    totp = AsyncMock()
    totp.verify_for_login.return_value = True

    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=user_repo,
        session_repo=session_repo,
        totp_service=totp,
    )
    challenge = token_service.issue_totp_challenge(user_id)
    pair = await svc.login_totp(challenge_token=challenge, code="123456", ip=None, user_agent=None)
    assert isinstance(pair, TokenPair)


@pytest.mark.asyncio
async def test_login_totp_wrong_code_rejected(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    user_id = uuid4()
    session_repo = AsyncMock()
    totp = AsyncMock()
    totp.verify_for_login.return_value = False

    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=AsyncMock(),
        session_repo=session_repo,
        totp_service=totp,
    )
    challenge = token_service.issue_totp_challenge(user_id)
    with pytest.raises(TotpInvalidCode):
        await svc.login_totp(challenge_token=challenge, code="000000", ip=None, user_agent=None)
    session_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_totp_forged_challenge_rejected(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    from src.iam.exceptions import TotpChallengeInvalid

    totp = AsyncMock()
    totp.verify_for_login.return_value = True
    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=AsyncMock(),
        totp_service=totp,
    )
    with pytest.raises(TotpChallengeInvalid):
        await svc.login_totp(
            challenge_token="not.a.valid.jwt", code="123456", ip=None, user_agent=None
        )
    # A verified access token must NOT be accepted as a challenge (type guard).
    access = token_service.issue_access_token(uuid4(), uuid4()).token
    with pytest.raises(TotpChallengeInvalid):
        await svc.login_totp(challenge_token=access, code="123456", ip=None, user_agent=None)


# ── session list / revoke authorization ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_flags_current(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    user_id = uuid4()
    current_id = uuid4()
    other_id = uuid4()
    now = datetime.now(UTC)
    session_repo = AsyncMock()
    session_repo.list_active_for_user.return_value = [
        SimpleNamespace(
            id=current_id,
            ip_address="1.1.1.1",
            user_agent="cur",
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=7),
        ),
        SimpleNamespace(
            id=other_id,
            ip_address=None,
            user_agent="other",
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=7),
        ),
    ]
    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=AsyncMock(),
        session_repo=session_repo,
    )
    sessions = await svc.list_sessions(user_id, current_session_id=current_id)
    by_id = {s.id: s for s in sessions}
    assert by_id[current_id].is_current is True
    assert by_id[other_id].is_current is False


@pytest.mark.asyncio
async def test_revoke_session_owned_ok(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    session_repo = AsyncMock()
    session_repo.revoke_for_user.return_value = 1  # one row → owned + revoked
    refresh_repo = AsyncMock()
    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=AsyncMock(),
        session_repo=session_repo,
        refresh_repo=refresh_repo,
    )
    sid = uuid4()
    await svc.revoke_session(uuid4(), sid)
    session_repo.revoke_for_user.assert_awaited_once()
    refresh_repo.revoke_for_session.assert_awaited_once_with(sid)


@pytest.mark.asyncio
async def test_revoke_session_not_owned_raises_404(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    session_repo = AsyncMock()
    session_repo.revoke_for_user.return_value = 0  # not owned / not found
    refresh_repo = AsyncMock()
    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=AsyncMock(),
        session_repo=session_repo,
        refresh_repo=refresh_repo,
    )
    with pytest.raises(UserNotFound):
        await svc.revoke_session(uuid4(), uuid4())
    # A cross-user / missing revoke must NOT touch refresh tokens.
    refresh_repo.revoke_for_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_all_others_keeps_current(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
) -> None:
    session_repo = AsyncMock()
    refresh_repo = AsyncMock()
    svc = _build(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        user_repo=AsyncMock(),
        session_repo=session_repo,
        refresh_repo=refresh_repo,
    )
    user_id, keep = uuid4(), uuid4()
    await svc.revoke_all_other_sessions(user_id, keep)
    session_repo.revoke_all_others_for_user.assert_awaited_once_with(
        user_id=user_id, keep_session_id=keep
    )
    refresh_repo.revoke_all_for_user_except_session.assert_awaited_once_with(
        user_id=user_id, keep_session_id=keep
    )
