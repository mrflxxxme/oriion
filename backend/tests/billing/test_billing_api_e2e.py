"""Phase 01.3 billing API — end-to-end (register → trial → billing endpoints).

Exercises the full vertical slice under RLS (override_get_db runs as the
non-superuser oriion_app): registering a user fires the real
TrialProvisioningService inside register()'s tenant-context block, then the
authed client reads the 5 billing endpoints. Covers the routers + schemas +
the register→trial hook + read services on the real path (AC-01.3.3 / .8).

App fixture mirrors tests/integration/test_e2e_auth_flow.py.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from fastapi import FastAPI

pytestmark = [pytest.mark.integration, pytest.mark.commit_required]


@pytest_asyncio.fixture
async def app(
    db_engine: AsyncEngine,
    db_session_committed: AsyncSession,  # TRUNCATE teardown between tests
) -> AsyncIterator[FastAPI]:
    from fakeredis import FakeAsyncRedis
    from src._shared.config import Settings, get_settings
    from src._shared.db.redis import get_redis
    from src._shared.db.session import get_db
    from src.iam.deps import get_email_sender
    from src.iam.services.email_service import InMemoryEmailSender
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

    production_app.dependency_overrides[get_settings] = lambda: test_settings
    production_app.dependency_overrides[get_db] = override_get_db
    production_app.dependency_overrides[get_email_sender] = lambda: shared_email_sender
    production_app.dependency_overrides[get_redis] = lambda: fake_redis
    production_app.state.test_email_sender = shared_email_sender  # type: ignore[attr-defined]

    try:
        yield production_app
    finally:
        production_app.dependency_overrides.clear()


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_verify_login(client: httpx.AsyncClient, app: FastAPI, email: str) -> str:
    """Register → verify-email → login; returns the Bearer access token."""
    password = "very-strong-password-123"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "consent_pdn": True, "display_name": "B"},
    )
    assert r.status_code == 201, r.text

    verification = app.state.test_email_sender.last()  # type: ignore[attr-defined]
    r = await client.post("/api/v1/auth/verify-email", json={"token": verification.token})
    assert r.status_code == 200, r.text

    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


async def test_billing_endpoints_after_register(app: FastAPI) -> None:
    """AC-01.3.3 + .8: register grants Trial; the 5 billing endpoints reflect it."""
    async with _client(app) as client:
        token = await _register_verify_login(client, app, "billing-e2e@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # credit-rate (global)
        r = await client.get("/api/v1/billing/credit-rate", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["rub_per_credit"] == "1"
        assert r.json()["wave"] == "0-1"

        # plans (global) — /plans returns self-serve-active tiers only;
        # enterprise is seeded active=false (custom/contact-sales) → excluded.
        r = await client.get("/api/v1/billing/plans", headers=headers)
        assert r.status_code == 200, r.text
        slugs = {p["slug"] for p in r.json()}
        assert slugs == {"trial", "solo", "team_5", "team_15", "team_30"}

        # subscription — Trial, active
        r = await client.get("/api/v1/billing/subscription", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["plan_slug"] == "trial"
        assert r.json()["status"] == "trial"

        # balance — 500 trial credits, no usage yet
        r = await client.get("/api/v1/billing/balance", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["balance_credits"] == "500.0000"
        assert body["hard_cap_credits"] == "500.0000"

        # transactions — the trial_grant row
        r = await client.get("/api/v1/billing/transactions", headers=headers)
        assert r.status_code == 200, r.text
        types = {t["transaction_type"] for t in r.json()}
        assert "trial_grant" in types


async def test_unauthenticated_billing_is_rejected(app: FastAPI) -> None:
    async with _client(app) as client:
        r = await client.get("/api/v1/billing/balance")
        assert r.status_code in (401, 403)
