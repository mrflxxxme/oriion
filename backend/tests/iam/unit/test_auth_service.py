"""Unit: AuthService — orchestration of register / login / refresh / logout /
verify / forgot / reset using mocked repositories + FakeRedis + InMemorySender."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from src._shared.config import Settings
from src.iam.exceptions import (
    ConsentMissing,
    EmailAlreadyRegistered,
    EmailNotVerified,
    InvalidCredentials,
    RateLimitExceeded,
    TokenNotFound,
    TokenRotationError,
)
from src.iam.schemas import LoginCommand, RegisterCommand
from src.iam.services.auth_service import AuthService
from src.iam.services.consent_service import ConsentService
from src.iam.services.email_service import InMemoryEmailSender
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService
from src.iam.services.token_service import TokenService


def _make_user(
    *,
    user_id: UUID | None = None,
    email: str = "user@x.dev",
    password_hash: str,
    email_verified_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id or uuid4(),
        email=email,
        password_hash=password_hash,
        email_verified_at=email_verified_at,
        created_at=datetime.now(UTC),
        deleted_at=None,
        display_name=None,
        locale="ru-RU",
        timezone="Europe/Moscow",
        updated_at=datetime.now(UTC),
    )


def _build_auth_service(
    *,
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
    user_repo: AsyncMock | None = None,
    session_repo: AsyncMock | None = None,
    refresh_repo: AsyncMock | None = None,
    consent_repo: AsyncMock | None = None,
    email_verif_repo: AsyncMock | None = None,
    password_reset_repo: AsyncMock | None = None,
    require_email_verification: bool = False,
) -> tuple[AuthService, dict[str, AsyncMock]]:
    user_repo = user_repo or AsyncMock()
    session_repo = session_repo or AsyncMock()
    refresh_repo = refresh_repo or AsyncMock()
    consent_repo = consent_repo or AsyncMock()
    email_verif_repo = email_verif_repo or AsyncMock()
    password_reset_repo = password_reset_repo or AsyncMock()
    consent_service = ConsentService(consent_repo, settings.consent_version_current)
    svc = AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        refresh_repo=refresh_repo,
        consent_repo=consent_repo,
        email_verif_repo=email_verif_repo,
        password_reset_repo=password_reset_repo,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        consent_service=consent_service,
        email_sender=email_sender,
        require_email_verification=require_email_verification,
        refresh_ttl_seconds=settings.refresh_ttl_seconds,
        access_ttl_seconds=settings.jwt_access_ttl_seconds,
    )
    return svc, {
        "user": user_repo,
        "session": session_repo,
        "refresh": refresh_repo,
        "consent": consent_repo,
        "email_verif": email_verif_repo,
        "password_reset": password_reset_repo,
    }


# ── register ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_happy_path_sends_email_and_returns_workspace(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    new_user = _make_user(password_hash="will-be-replaced-by-service")
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = None
    user_repo.create.return_value = new_user
    consent_repo = AsyncMock()
    consent_repo.record.return_value = SimpleNamespace(id=uuid4(), granted_at=datetime.now(UTC))
    email_verif_repo = AsyncMock()
    email_verif_repo.create.return_value = SimpleNamespace(id=uuid4())

    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
        consent_repo=consent_repo,
        email_verif_repo=email_verif_repo,
    )

    result = await svc.register(
        RegisterCommand(
            email="new@x.dev",
            password="strong-password-123",
            consent_pdn=True,
            ip="1.2.3.4",
            user_agent="pytest",
        )
    )

    assert result.user_id == new_user.id
    assert result.workspace_id is not None
    assert result.cell_id is not None
    assert result.email_verification_sent is True

    mocks["user"].create.assert_awaited_once()
    mocks["consent"].record.assert_awaited()
    assert len(email_sender.outbox) == 1
    assert email_sender.outbox[0].kind == "verification"
    assert email_sender.outbox[0].to == new_user.email


@pytest.mark.asyncio
async def test_register_without_consent_raises(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
    )
    with pytest.raises(ConsentMissing):
        await svc.register(
            RegisterCommand(
                email="new@x.dev",
                password="strong-password-123",
                consent_pdn=False,
            )
        )


@pytest.mark.asyncio
async def test_register_email_exists_raises_409(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = _make_user(password_hash="x")
    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
    )
    with pytest.raises(EmailAlreadyRegistered):
        await svc.register(
            RegisterCommand(
                email="dup@x.dev",
                password="strong-password-123",
                consent_pdn=True,
                ip="1.1.1.1",
            )
        )


@pytest.mark.asyncio
async def test_register_rate_limited(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    # Burn the (ip,email) bucket
    for _ in range(5):
        await rate_limit_service.check_and_increment(
            scope="register", ip="9.9.9.9", email="r@x.dev"
        )

    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
    )
    with pytest.raises(RateLimitExceeded):
        await svc.register(
            RegisterCommand(
                email="r@x.dev",
                password="strong-password-123",
                consent_pdn=True,
                ip="9.9.9.9",
            )
        )


# ── login ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_returns_token_pair(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    pw_hash = password_service.hash("S3cret-pass!")
    user = _make_user(password_hash=pw_hash, email_verified_at=datetime.now(UTC))
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    session_repo = AsyncMock()
    session_repo.create.return_value = SimpleNamespace(
        id=uuid4(),
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    refresh_repo = AsyncMock()

    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
        session_repo=session_repo,
        refresh_repo=refresh_repo,
    )
    pair = await svc.login(LoginCommand(email=user.email, password="S3cret-pass!", ip="1.1.1.1"))
    assert pair.access_token
    assert pair.refresh_token
    assert pair.expires_in == 900
    assert pair.token_type == "Bearer"


@pytest.mark.asyncio
async def test_login_invalid_password_raises(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    user = _make_user(password_hash=password_service.hash("S3cret"))
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user

    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
    )
    with pytest.raises(InvalidCredentials):
        await svc.login(LoginCommand(email=user.email, password="wrong"))


@pytest.mark.asyncio
async def test_login_unknown_email_raises_invalid_credentials(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = None
    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
    )
    with pytest.raises(InvalidCredentials):
        await svc.login(LoginCommand(email="ghost@x.dev", password="anything"))


@pytest.mark.asyncio
async def test_login_email_not_verified_when_gate_on(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    user = _make_user(password_hash=password_service.hash("Pw"), email_verified_at=None)
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
        require_email_verification=True,
    )
    with pytest.raises(EmailNotVerified):
        await svc.login(LoginCommand(email=user.email, password="Pw"))


# ── refresh rotation chain-revoke ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_chain(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    used_row = SimpleNamespace(
        id=uuid4(),
        session_id=uuid4(),
        rotation_chain_id=uuid4(),
        used_at=datetime.now(UTC),
        revoked_at=None,
    )
    refresh_repo = AsyncMock()
    refresh_repo.find_by_hash.return_value = used_row

    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        refresh_repo=refresh_repo,
    )
    with pytest.raises(TokenRotationError):
        await svc.rotate_refresh("any-plaintext", ip="1.1.1.1", user_agent="ua")
    mocks["refresh"].revoke_chain.assert_awaited_once_with(used_row.rotation_chain_id)
    mocks["session"].revoke.assert_awaited_once_with(used_row.session_id)


@pytest.mark.asyncio
async def test_refresh_happy_path_issues_new_pair(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    session_id, user_id, chain_id = uuid4(), uuid4(), uuid4()
    valid_old = SimpleNamespace(
        id=uuid4(),
        session_id=session_id,
        rotation_chain_id=chain_id,
        used_at=None,
        revoked_at=None,
    )
    refresh_repo = AsyncMock()
    refresh_repo.find_by_hash.return_value = valid_old
    refresh_repo.create.return_value = SimpleNamespace(id=uuid4())

    session = SimpleNamespace(id=session_id, user_id=user_id, revoked_at=None)
    session_repo = AsyncMock()
    session_repo.find_by_id.return_value = session

    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        refresh_repo=refresh_repo,
        session_repo=session_repo,
    )

    pair = await svc.rotate_refresh("plain", ip=None, user_agent=None)
    assert pair.access_token
    assert pair.refresh_token
    mocks["refresh"].mark_used_and_link.assert_awaited_once()


# ── logout ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_revokes_session_and_chain(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    row = SimpleNamespace(id=uuid4(), session_id=uuid4(), rotation_chain_id=uuid4())
    refresh_repo = AsyncMock()
    refresh_repo.find_by_hash.return_value = row
    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        refresh_repo=refresh_repo,
    )
    jti = uuid4()
    await svc.logout("plain", access_jti=jti, access_remaining_ttl=120)
    mocks["session"].revoke.assert_awaited_once_with(row.session_id)
    mocks["refresh"].revoke_chain.assert_awaited_once_with(row.rotation_chain_id)


@pytest.mark.asyncio
async def test_logout_unknown_token_is_idempotent(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    refresh_repo = AsyncMock()
    refresh_repo.find_by_hash.return_value = None
    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        refresh_repo=refresh_repo,
    )
    await svc.logout("ghost-token")
    mocks["session"].revoke.assert_not_called()


# ── verify-email ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_email_happy_path_marks_user(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    plaintext = "plain-token"
    row = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=None,
    )
    email_verif_repo = AsyncMock()
    email_verif_repo.find_active_by_hash.return_value = row
    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        email_verif_repo=email_verif_repo,
    )
    await svc.verify_email(plaintext)
    mocks["email_verif"].mark_used.assert_awaited_once_with(row.id)
    mocks["user"].mark_email_verified.assert_awaited_once_with(row.user_id)


@pytest.mark.asyncio
async def test_verify_email_expired_raises_token_not_found(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    row = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        used_at=None,
    )
    email_verif_repo = AsyncMock()
    email_verif_repo.find_active_by_hash.return_value = row
    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        email_verif_repo=email_verif_repo,
    )
    with pytest.raises(TokenNotFound):
        await svc.verify_email("plain")


# ── anti-enum forgot-password ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_silent(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = None
    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
    )
    await svc.forgot_password("ghost@x.dev", ip="1.1.1.1", user_agent=None)
    mocks["password_reset"].create.assert_not_called()
    assert email_sender.outbox == []


@pytest.mark.asyncio
async def test_forgot_password_known_email_sends_reset(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    user = _make_user(password_hash=password_service.hash("Pw"))
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    password_reset_repo = AsyncMock()
    password_reset_repo.create.return_value = SimpleNamespace(id=uuid4())

    svc, _ = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        user_repo=user_repo,
        password_reset_repo=password_reset_repo,
    )
    await svc.forgot_password(user.email, ip="1.1.1.1", user_agent=None)
    assert len(email_sender.outbox) == 1
    assert email_sender.outbox[0].kind == "password_reset"


# ── reset-password chain-revoke ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_password_reuse_revokes_chain_and_sessions(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    consumed = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        reset_chain_id=uuid4(),
        used_at=datetime.now(UTC),
        revoked_at=None,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    password_reset_repo = AsyncMock()
    password_reset_repo.find_by_hash.return_value = consumed
    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        password_reset_repo=password_reset_repo,
    )
    with pytest.raises(TokenNotFound):
        await svc.reset_password("plain", "new-strong-pass-123")
    mocks["password_reset"].revoke_chain.assert_awaited_once_with(consumed.reset_chain_id)
    mocks["session"].revoke_all_for_user.assert_awaited_once_with(consumed.user_id)


@pytest.mark.asyncio
async def test_reset_password_happy_path(
    settings: Settings,
    password_service: PasswordService,
    token_service: TokenService,
    rate_limit_service: RateLimitService,
    email_sender: InMemoryEmailSender,
) -> None:
    valid = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        reset_chain_id=uuid4(),
        used_at=None,
        revoked_at=None,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    password_reset_repo = AsyncMock()
    password_reset_repo.find_by_hash.return_value = valid
    svc, mocks = _build_auth_service(
        settings=settings,
        password_service=password_service,
        token_service=token_service,
        rate_limit_service=rate_limit_service,
        email_sender=email_sender,
        password_reset_repo=password_reset_repo,
    )
    await svc.reset_password("plain", "new-strong-pass-123")
    mocks["user"].update_password_hash.assert_awaited_once()
    mocks["password_reset"].mark_used.assert_awaited_once_with(valid.id)
    mocks["session"].revoke_all_for_user.assert_awaited_once_with(valid.user_id)
