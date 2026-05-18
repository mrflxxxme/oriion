"""Unit: routers — endpoint routing + dependency-override happy paths.

Uses FastAPI dependency_overrides + AsyncMock AuthService so we don't touch
DB/Redis. Verifies status codes, response shapes, and that the router maps
service calls correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from src.iam.deps import get_auth_service
from src.iam.exceptions import (
    ConsentMissing,
    EmailAlreadyRegistered,
    InvalidCredentials,
    RateLimitExceeded,
    TokenNotFound,
    TokenRotationError,
)
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.iam.schemas import RegisterResult, TokenPair, UserResponse
from src.main import app


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_auth_service: AsyncMock) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    c = TestClient(app)
    yield c  # type: ignore[misc]
    app.dependency_overrides.clear()


def _u() -> UUID:
    return uuid4()


# ── register ──────────────────────────────────────────────────────────────


def test_register_201(client: TestClient, mock_auth_service: AsyncMock) -> None:
    uid, ws, cell = _u(), _u(), _u()
    mock_auth_service.register.return_value = RegisterResult(
        user_id=uid,
        workspace_id=ws,
        cell_id=cell,
        email="new@x.dev",
        email_verification_sent=True,
    )
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@x.dev",
            "password": "strong-password-123",
            "consent_pdn": True,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == str(uid)
    assert body["workspace_id"] == str(ws)
    assert body["cell_id"] == str(cell)


def test_register_consent_missing_422(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.register.side_effect = ConsentMissing()
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@y.dev",
            "password": "strong-password-123",
            "consent_pdn": False,
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "iam.consent.pdn_missing"
    assert r.headers["content-type"].startswith("application/problem+json")


def test_register_email_conflict_409(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.register.side_effect = EmailAlreadyRegistered()
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@x.dev",
            "password": "strong-password-123",
            "consent_pdn": True,
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "iam.auth.email_already_registered"


def test_register_rate_limit_429_with_retry_after(
    client: TestClient, mock_auth_service: AsyncMock
) -> None:
    mock_auth_service.register.side_effect = RateLimitExceeded(retry_after=60)
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@y.dev",
            "password": "strong-password-123",
            "consent_pdn": True,
        },
    )
    assert r.status_code == 429
    assert r.headers["retry-after"] == "60"


# ── login ─────────────────────────────────────────────────────────────────


def test_login_200(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.login.return_value = TokenPair(
        access_token="A", refresh_token="R", expires_in=900
    )
    r = client.post("/api/v1/auth/login", json={"email": "u@x.dev", "password": "Pw"})
    assert r.status_code == 200
    assert r.json() == {
        "access_token": "A",
        "refresh_token": "R",
        "expires_in": 900,
        "token_type": "Bearer",
    }


def test_login_invalid_credentials_401(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.login.side_effect = InvalidCredentials()
    r = client.post("/api/v1/auth/login", json={"email": "u@x.dev", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["code"] == "iam.auth.invalid_credentials"


# ── refresh ───────────────────────────────────────────────────────────────


def test_refresh_200(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.rotate_refresh.return_value = TokenPair(
        access_token="A2", refresh_token="R2", expires_in=900
    )
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "old"})
    assert r.status_code == 200
    assert r.json()["access_token"] == "A2"


def test_refresh_chain_revoke_401(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.rotate_refresh.side_effect = TokenRotationError("reused")
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "stale"})
    assert r.status_code == 401
    assert r.json()["code"] == "iam.auth.refresh_rotation_violation"


# ── logout ────────────────────────────────────────────────────────────────


def test_logout_204(client: TestClient, mock_auth_service: AsyncMock) -> None:
    r = client.post("/api/v1/auth/logout", json={"refresh_token": "any"})
    assert r.status_code == 204


# ── verify-email ──────────────────────────────────────────────────────────


def test_verify_email_200(client: TestClient, mock_auth_service: AsyncMock) -> None:
    r = client.post("/api/v1/auth/verify-email", json={"token": "plaintext"})
    assert r.status_code == 200
    assert r.json()["status"] == "verified"


def test_verify_email_410(client: TestClient, mock_auth_service: AsyncMock) -> None:
    mock_auth_service.verify_email.side_effect = TokenNotFound()
    r = client.post("/api/v1/auth/verify-email", json={"token": "stale"})
    assert r.status_code == 410


# ── resend / forgot — anti-enum 202 ───────────────────────────────────────


def test_resend_verification_202(client: TestClient, mock_auth_service: AsyncMock) -> None:
    r = client.post("/api/v1/auth/resend-verification", json={"email": "x@y.dev"})
    assert r.status_code == 202


def test_forgot_password_202(client: TestClient, mock_auth_service: AsyncMock) -> None:
    r = client.post("/api/v1/auth/forgot-password", json={"email": "x@y.dev"})
    assert r.status_code == 202


# ── reset-password ────────────────────────────────────────────────────────


def test_reset_password_200(client: TestClient, mock_auth_service: AsyncMock) -> None:
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "plain", "new_password": "new-strong-pw-12"},
    )
    assert r.status_code == 200


def test_reset_password_token_not_found_410(
    client: TestClient, mock_auth_service: AsyncMock
) -> None:
    mock_auth_service.reset_password.side_effect = TokenNotFound()
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "stale", "new_password": "new-strong-pw-12"},
    )
    assert r.status_code == 410


# ── /users/me ─────────────────────────────────────────────────────────────


def test_get_me_401_without_auth(client: TestClient) -> None:
    r = client.get("/api/v1/users/me")
    # No Authorization header — TokenInvalid surfaces as 401 problem+json
    assert r.status_code == 401


def test_get_me_200_with_override(client: TestClient) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="u@x.dev",
        email_verified_at=datetime.now(UTC),
        display_name="Анна",
        locale="ru-RU",
        timezone="Europe/Moscow",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    async def fake_user() -> AuthenticatedUser:
        return AuthenticatedUser(claims=None, user=user)  # type: ignore[arg-type]

    app.dependency_overrides[get_current_user] = fake_user
    try:
        r = client.get("/api/v1/users/me")
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "u@x.dev"
        assert body["display_name"] == "Анна"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_patch_me_200(client: TestClient, mock_auth_service: AsyncMock) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="u@x.dev",
        email_verified_at=None,
        display_name=None,
        locale="ru-RU",
        timezone="Europe/Moscow",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    async def fake_user() -> AuthenticatedUser:
        return AuthenticatedUser(claims=None, user=user)  # type: ignore[arg-type]

    updated = SimpleNamespace(
        id=user.id,
        email=user.email,
        email_verified_at=None,
        display_name="New",
        locale="ru-RU",
        timezone="Europe/Moscow",
        created_at=user.created_at,
        updated_at=datetime.now(UTC),
    )
    mock_auth_service.update_user_profile.return_value = UserResponse.model_validate(updated)

    app.dependency_overrides[get_current_user] = fake_user
    try:
        r = client.patch("/api/v1/users/me", json={"display_name": "New"})
        assert r.status_code == 200
        assert r.json()["display_name"] == "New"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── health (sanity) ───────────────────────────────────────────────────────


def test_health_still_works(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
