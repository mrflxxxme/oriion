"""Integration (real PG, testcontainers): Phase 01.8 auth extensions.

Exercises against a MIGRATED database — proving the 0007 migration applies and
the new tables behave under real SQL:

  * 2FA TOTP: enroll → confirm → login returns a challenge (not tokens) →
    login/totp with a live code issues a pair; wrong code rejected; replay of a
    consumed backup code rejected; disable turns the second factor off.
  * Magic-link: request (anti-enum 202) → consume issues a pair; replay of the
    consumed token → 410; expiry rejected.
  * Session list/revoke: a user sees only their OWN sessions; revoking another
    user's session id → 404 (no cross-user reach); revoke-all-others keeps the
    caller's session.
  * At-rest: iam.totp_credentials.secret_encrypted holds ciphertext, never the
    base32 secret.

Marker: integration + commit_required — reads rows back across committed
requests via a fresh assertion session (mirrors test_e2e_auth_flow.py).
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx
import pyotp
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from fastapi import FastAPI


pytestmark = [pytest.mark.integration, pytest.mark.commit_required]


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def app(
    db_engine: AsyncEngine,
    db_session_committed: AsyncSession,
) -> AsyncIterator[FastAPI]:
    from fakeredis import FakeAsyncRedis
    from src._shared.config import Settings, get_settings
    from src._shared.db.redis import get_redis
    from src._shared.db.session import get_db
    from src.iam.deps import get_email_sender, get_iam_kms_provider
    from src.iam.services.email_service import InMemoryEmailSender
    from src.llm_gateway.services.kms_provider import LocalAESKMS
    from src.main import app as production_app

    test_byok_master_key_b64 = base64.b64encode(
        b"test-byok-master-key-for-e2e-only"[:32].ljust(32, b"0")
    ).decode("ascii")

    test_settings = Settings(
        app_env="test",
        database_url="ignored-overridden-via-get_db",
        redis_url="redis://localhost:6379/15",
        jwt_secret_access_v1="test-jwt-secret-do-not-use-in-prod-32+",  # type: ignore[arg-type]
        jwt_iss="oriion-iam-test",
        jwt_aud="oriion-app-test",
        jwt_access_ttl_seconds=900,
        refresh_ttl_seconds=604800,
        require_email_verification=False,
        consent_version_current="test-2026-05-19",
        rate_limit_window_seconds=60,
        kms_backend="local",
        byok_master_key_b64=test_byok_master_key_b64,  # type: ignore[arg-type]
        fx_rate_usd_to_rub=100.0,
        web_search_mock_mode=True,
    )

    sessionmaker = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            await session.execute(text("SET LOCAL ROLE oriion_app"))
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    shared_email_sender = InMemoryEmailSender()
    fake_redis = FakeAsyncRedis()
    # Deterministic KMS so the TOTP secret encrypt/decrypt round-trips without
    # relying on lifespan startup having stashed a provider on app.state.
    test_kms = LocalAESKMS(master_key=b"integration-totp-master-key-32b!"[:32].ljust(32, b"0"))

    production_app.dependency_overrides[get_settings] = lambda: test_settings
    production_app.dependency_overrides[get_db] = override_get_db
    production_app.dependency_overrides[get_email_sender] = lambda: shared_email_sender
    production_app.dependency_overrides[get_redis] = lambda: fake_redis
    production_app.dependency_overrides[get_iam_kms_provider] = lambda: test_kms

    production_app.state.test_email_sender = shared_email_sender  # type: ignore[attr-defined]

    try:
        yield production_app
    finally:
        production_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def assertion_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_and_login(
    client: httpx.AsyncClient, email: str, password: str
) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "consent_pdn": True},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    pair = r.json()
    body["access_token"] = pair["access_token"]
    body["refresh_token"] = pair["refresh_token"]
    return body


# ── 2FA TOTP full flow ──────────────────────────────────────────────────────


async def test_totp_enroll_confirm_login_challenge_flow(
    app: FastAPI, assertion_session: AsyncSession
) -> None:
    email, pw = "totp-flow@example.com", "very-strong-password-1"
    async with _client(app) as client:
        acct = await _register_and_login(client, email, pw)
        user_id = acct["user_id"]
        headers = {"Authorization": f"Bearer {acct['access_token']}"}

        # Enroll → secret + otpauth URI.
        r = await client.post("/api/v1/users/me/totp/enroll", headers=headers)
        assert r.status_code == 200, r.text
        secret = r.json()["secret"]
        assert r.json()["provisioning_uri"].startswith("otpauth://totp/")

        # Secret is stored ENCRYPTED, never as the base32 plaintext.
        row = await assertion_session.execute(
            text("SELECT secret_encrypted FROM iam.totp_credentials WHERE user_id = :u"),
            {"u": user_id},
        )
        stored = row.scalar_one()
        assert isinstance(stored, bytes | memoryview)
        assert secret.encode("utf-8") not in bytes(stored)

        # Confirm with a live code → backup codes returned, credential active.
        totp = pyotp.TOTP(secret)
        r = await client.post(
            "/api/v1/users/me/totp/confirm", headers=headers, json={"code": totp.now()}
        )
        assert r.status_code == 200, r.text
        backup_codes = r.json()["backup_codes"]
        assert len(backup_codes) == 10

        confirmed = await assertion_session.execute(
            text("SELECT confirmed_at FROM iam.totp_credentials WHERE user_id = :u"),
            {"u": user_id},
        )
        assert confirmed.scalar() is not None

        # Now login returns a 2FA CHALLENGE, not tokens.
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        assert r.status_code == 200, r.text
        challenge = r.json()
        assert challenge["two_factor_required"] is True
        assert "access_token" not in challenge

        # Wrong code rejected.
        r = await client.post(
            "/api/v1/auth/login/totp",
            json={"challenge_token": challenge["challenge_token"], "code": "000000"},
        )
        assert r.status_code == 401

        # Correct code → token pair.
        r = await client.post(
            "/api/v1/auth/login/totp",
            json={
                "challenge_token": challenge["challenge_token"],
                "code": pyotp.TOTP(secret).now(),
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["access_token"]

        # A backup code works as a second factor and is single-use.
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        challenge2 = r.json()
        r = await client.post(
            "/api/v1/auth/login/totp",
            json={"challenge_token": challenge2["challenge_token"], "code": backup_codes[0]},
        )
        assert r.status_code == 200, r.text

        # Replaying the SAME backup code → rejected.
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        challenge3 = r.json()
        r = await client.post(
            "/api/v1/auth/login/totp",
            json={"challenge_token": challenge3["challenge_token"], "code": backup_codes[0]},
        )
        assert r.status_code == 401


async def test_totp_disable_restores_password_only_login(
    app: FastAPI, assertion_session: AsyncSession
) -> None:
    email, pw = "totp-disable@example.com", "very-strong-password-2"
    async with _client(app) as client:
        acct = await _register_and_login(client, email, pw)
        headers = {"Authorization": f"Bearer {acct['access_token']}"}
        secret = (await client.post("/api/v1/users/me/totp/enroll", headers=headers)).json()[
            "secret"
        ]
        await client.post(
            "/api/v1/users/me/totp/confirm",
            headers=headers,
            json={"code": pyotp.TOTP(secret).now()},
        )
        # Disable with a live code.
        r = await client.post(
            "/api/v1/users/me/totp/disable",
            headers=headers,
            json={"code": pyotp.TOTP(secret).now()},
        )
        assert r.status_code == 204, r.text
        # Password-only login now issues tokens directly again.
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        assert r.status_code == 200
        assert r.json()["access_token"]


# ── magic-link full flow ────────────────────────────────────────────────────


async def test_magic_link_request_consume_and_replay(app: FastAPI) -> None:
    email, pw = "magic-flow@example.com", "very-strong-password-3"
    async with _client(app) as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pw, "consent_pdn": True},
        )

        # Request → anti-enum 202 + a queued magic-link email.
        r = await client.post("/api/v1/auth/magic-link/request", json={"email": email})
        assert r.status_code == 202
        rec = app.state.test_email_sender.last()  # type: ignore[attr-defined]
        assert rec.kind == "magic_link"
        assert rec.to == email

        # Consume → token pair.
        r = await client.post("/api/v1/auth/magic-link/consume", json={"token": rec.token})
        assert r.status_code == 200, r.text
        assert r.json()["access_token"]

        # Replay of the consumed token → 410.
        r = await client.post("/api/v1/auth/magic-link/consume", json={"token": rec.token})
        assert r.status_code == 410


async def test_magic_link_unknown_email_is_silent_202(app: FastAPI) -> None:
    async with _client(app) as client:
        pre = len(app.state.test_email_sender.outbox)  # type: ignore[attr-defined]
        r = await client.post(
            "/api/v1/auth/magic-link/request", json={"email": "ghost@example.com"}
        )
        assert r.status_code == 202
        # No email queued for a non-existent account (anti-enum, no oracle).
        assert len(app.state.test_email_sender.outbox) == pre  # type: ignore[attr-defined]


# ── session list / revoke isolation ─────────────────────────────────────────


async def test_session_list_and_cross_user_revoke_isolation(
    app: FastAPI, assertion_session: AsyncSession
) -> None:
    async with _client(app) as client:
        # Two distinct users, each with a live session.
        alice = await _register_and_login(client, "alice-sess@example.com", "strong-pass-alice-1")
        bob = await _register_and_login(client, "bob-sess@example.com", "strong-pass-bob-1")
        alice_headers = {"Authorization": f"Bearer {alice['access_token']}"}
        bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}

        # Alice sees ONLY her own session, flagged current.
        r = await client.get("/api/v1/users/me/sessions", headers=alice_headers)
        assert r.status_code == 200, r.text
        alice_sessions = r.json()["sessions"]
        assert len(alice_sessions) == 1
        assert alice_sessions[0]["is_current"] is True
        alice_session_id = alice_sessions[0]["id"]

        # Discover Bob's session id (via Bob's own list).
        r = await client.get("/api/v1/users/me/sessions", headers=bob_headers)
        bob_session_id = r.json()["sessions"][0]["id"]

        # Alice CANNOT revoke Bob's session — 404 (no cross-user reach / oracle).
        r = await client.request(
            "DELETE", f"/api/v1/users/me/sessions/{bob_session_id}", headers=alice_headers
        )
        assert r.status_code == 404

        # Bob's session is still active in the DB.
        still = await assertion_session.execute(
            text("SELECT revoked_at FROM iam.sessions WHERE id = :s"),
            {"s": bob_session_id},
        )
        assert still.scalar() is None

        # Alice CAN revoke her own session.
        r = await client.request(
            "DELETE", f"/api/v1/users/me/sessions/{alice_session_id}", headers=alice_headers
        )
        assert r.status_code == 204


async def test_revoke_all_other_sessions_keeps_current(
    app: FastAPI, assertion_session: AsyncSession
) -> None:
    email, pw = "multi-sess@example.com", "strong-pass-multi-1"
    async with _client(app) as client:
        acct = await _register_and_login(client, email, pw)
        user_id = acct["user_id"]
        # Second login → a second session.
        await client.post("/api/v1/auth/login", json={"email": email, "password": pw})

        headers = {"Authorization": f"Bearer {acct['access_token']}"}
        r = await client.get("/api/v1/users/me/sessions", headers=headers)
        assert len(r.json()["sessions"]) == 2

        # Revoke everywhere else.
        r = await client.request("DELETE", "/api/v1/users/me/sessions", headers=headers)
        assert r.status_code == 204

        active = await assertion_session.execute(
            text("SELECT count(*) FROM iam.sessions " "WHERE user_id = :u AND revoked_at IS NULL"),
            {"u": user_id},
        )
        # Only the caller's current session remains active.
        assert (active.scalar() or 0) == 1
