"""Unit: middleware.get_current_user — header parsing + token decode."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.iam.exceptions import TokenInvalid
from src.iam.middleware import _extract_bearer, get_current_user
from src.iam.services.token_service import TokenService


def test_extract_bearer_missing_raises() -> None:
    with pytest.raises(TokenInvalid):
        _extract_bearer(None)


def test_extract_bearer_malformed_raises() -> None:
    with pytest.raises(TokenInvalid):
        _extract_bearer("Basic abc")
    with pytest.raises(TokenInvalid):
        _extract_bearer("Bearer")
    with pytest.raises(TokenInvalid):
        _extract_bearer("")


def test_extract_bearer_happy() -> None:
    assert _extract_bearer("Bearer xyz.abc.123") == "xyz.abc.123"
    # split(maxsplit=1) collapses run of whitespace between scheme and token
    assert _extract_bearer("bearer  token-with-leading-collapse") == "token-with-leading-collapse"


@pytest.mark.asyncio
async def test_get_current_user_returns_user_for_valid_bearer(
    token_service: TokenService,
) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="u@x.dev",
        password_hash="$argon2id$...",
        email_verified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        deleted_at=None,
        display_name=None,
        locale="ru-RU",
        timezone="Europe/Moscow",
        updated_at=datetime.now(UTC),
    )
    sid = uuid4()
    issued = token_service.issue_access_token(user_id=user.id, session_id=sid)

    # Mock DB — UserRepository is constructed with a session-like; we patch
    # get_current_user end-to-end via direct call passing dependencies.
    db_session = MagicMock()
    db_session.get = AsyncMock(return_value=user)

    auth = await get_current_user(
        authorization=f"Bearer {issued.token}",
        db=db_session,
        token_service=token_service,
    )
    assert auth.user is user
    assert auth.claims.sub == user.id
    assert auth.claims.sid == sid


@pytest.mark.asyncio
async def test_get_current_user_deleted_user_raises(
    token_service: TokenService,
) -> None:
    deleted_user = SimpleNamespace(
        id=uuid4(),
        deleted_at=datetime.now(UTC),
    )
    issued = token_service.issue_access_token(user_id=deleted_user.id, session_id=uuid4())
    db_session = MagicMock()
    db_session.get = AsyncMock(return_value=deleted_user)
    with pytest.raises(TokenInvalid):
        await get_current_user(
            authorization=f"Bearer {issued.token}",
            db=db_session,
            token_service=token_service,
        )
