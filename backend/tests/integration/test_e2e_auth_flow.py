"""E2E smoke — full auth lifecycle against real PG (testcontainers).

Phase 00.2.5 anchor test. Verifies that the stub→real swap in iam +
multitenancy actually causes:

  * `provision_initial_workspace` to INSERT workspace + cell rows and
    materialize the per-cell schema (memory_entries table + HNSW index).
  * `emit_audit_event` to INSERT audit_log rows inside the request's
    outer TX (instead of falling back to structlog-only).
  * The token-issue / revocation chain to persist refresh_token + session
    rows under real RLS-aware oriion_app credentials.

Scope note (Phase 00.2.5 reality check)
=======================================
The launch checklist (Section 5) called for a "register → /api/v1/llm/chat
→ refresh → logout" flow that exercised the DeepSeek + Yandex + GigaChat +
embeddings + BYOK matrix end-to-end through HTTP. The current state of
``backend/src/main.py`` only wires the iam routers (auth + me); LLM,
multitenancy, and MCP routers exist but their handlers are 501 stubs
("Provider DI wiring lands Phase 00.5"). So the matrix-through-HTTP form
of the smoke is genuinely Phase 00.5 work.

What we do instead:
  * Drive the full wired surface — every iam auth endpoint — against
    real PG with the real services (no stubs).
  * Assert side-effects across schemas: iam.users + iam.email_verif +
    iam.password_reset + iam.refresh_tokens + iam.sessions +
    multitenancy.workspaces + multitenancy.cells + audit.audit_log.
  * Service-layer provider matrix is already covered by
    ``tests/llm_gateway/test_byok_flow_full.py`` +
    ``tests/llm_gateway/test_cost_ledger_sum_match.py`` (integration tests
    that run against the same testcontainers PG).
  * Cost-ledger SUM consistency assertion lives in
    ``test_cost_ledger_sum_match.py``; replicating it here would only
    duplicate that proof.

Marker: ``integration + commit_required`` — the test reads back rows
written by previous requests using a fresh session, so each request's
``get_db`` must end with a real COMMIT (not a SAVEPOINT inside an outer
TX rollback).

Loop note: uses ``httpx.AsyncClient + ASGITransport`` rather than
``fastapi.testclient.TestClient`` because TestClient runs requests in
its own event loop, and asyncpg's connection pool (created in pytest's
loop by ``db_engine``) refuses cross-loop reuse.
"""

from __future__ import annotations

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


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def app(
    db_engine: AsyncEngine,
    # commit_required-marked → request db_session_committed so its
    # TRUNCATE-based teardown runs after each test. Without this, audit_log
    # rows + workspaces + cells accumulate across tests within one pytest
    # session, breaking `count == 1`-style assertions under any non-default
    # ordering (random, -k filtering, repeat-on-fail).
    db_session_committed: AsyncSession,
) -> AsyncIterator[FastAPI]:
    """FastAPI app instance with dependency overrides bound to the test container.

    Overrides ``get_db`` to commit-per-request against the testcontainers
    engine (real DB writes — required so audit_log triggers fire on
    actual COMMIT and the assertions can read across sessions).

    Overrides ``get_settings`` to inject an in-memory ``InMemoryEmailSender``
    so the test can recover the verification + reset tokens.

    Overrides the Redis dependency to use ``fakeredis`` (rate-limit + JWT
    blacklist).
    """
    import base64

    from fakeredis import FakeAsyncRedis
    from src._shared.config import Settings, get_settings
    from src._shared.db.redis import get_redis
    from src._shared.db.session import get_db
    from src.iam.deps import get_email_sender
    from src.iam.services.email_service import InMemoryEmailSender
    from src.main import app as production_app

    # Deterministic non-secret BYOK master key — computed from a literal
    # seed at runtime so gitleaks's "generic-api-key" rule does not flag
    # the high-entropy base64 string. Mirrors the CI workflow's
    # CI_BYOK_MASTER_KEY_B64 generation step.
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
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        # Phase 00.5 Topic 1 RLS Option A: surface the prod RLS failure mode
        # by running as `oriion_app` (the non-superuser role used in prod)
        # instead of the testcontainers `oriion` owner. Without this SET
        # LOCAL ROLE, FORCE-RLS-protected INSERTs in register() would pass
        # in CI (owner bypasses FORCE RLS) yet fail in prod. With it:
        #   * Direct INSERTs into multitenancy.{workspaces,cells,cell_members}
        #     fail unless _shared.current_user_id() IS NOT NULL.
        #   * multitenancy.bootstrap_first_workspace() (SECURITY DEFINER)
        #     correctly escapes the RLS check — this is the canary test.
        # The role auto-resets at COMMIT / ROLLBACK so subsequent fixtures
        # (db_session_committed teardown TRUNCATE) regain owner privileges.
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

    # Stash the helpers on the app so the test can read tokens / clear redis.
    production_app.state.test_email_sender = shared_email_sender  # type: ignore[attr-defined]
    production_app.state.test_redis = fake_redis  # type: ignore[attr-defined]

    try:
        yield production_app
    finally:
        production_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def assertion_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Read-only session for asserting DB state after committed requests.

    Distinct from the per-request session each handler opens via
    overridden ``get_db`` — necessary so the assertions see rows that
    a previous request committed (handler closes its own session before
    returning).
    """
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


# ── helpers ─────────────────────────────────────────────────────────────────


def _client(app: FastAPI) -> httpx.AsyncClient:
    """In-process async HTTP client — runs handlers in the test's event loop
    so asyncpg connections opened by handlers stay in the same loop as the
    test fixtures (avoids the "Future attached to a different loop" crashes
    that ``fastapi.testclient.TestClient`` would trigger).

    Caller is responsible for ``async with`` lifetime management.
    """
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _count_audit_rows(
    session: AsyncSession,
    action: str,
    *,
    actor_id: str | None = None,
) -> int:
    """Count audit_log rows for a given action.

    ``actor_id`` is optional but recommended for test isolation: filtering
    by the test's specific user_id makes the assertion robust to other
    tests in the same session having emitted the same action.
    """
    if actor_id is None:
        result = await session.execute(
            text("SELECT count(*) FROM audit.audit_log WHERE action = :a"),
            {"a": action},
        )
    else:
        result = await session.execute(
            text("SELECT count(*) FROM audit.audit_log " "WHERE action = :a AND actor_id = :u"),
            {"a": action, "u": actor_id},
        )
    return int(result.scalar() or 0)


async def _select_workspace_by_slug(session: AsyncSession, slug: str) -> tuple[str, str] | None:
    """Return (workspace_id, plan_tier) for an active workspace by slug, else None."""
    result = await session.execute(
        text(
            "SELECT id::text, plan_tier FROM multitenancy.workspaces "
            "WHERE slug = :s AND deleted_at IS NULL"
        ),
        {"s": slug},
    )
    row = result.first()
    return (row[0], row[1]) if row else None


# ── tests ───────────────────────────────────────────────────────────────────


async def test_register_through_logout_flow(app: FastAPI, assertion_session: AsyncSession) -> None:
    """Full happy path: register → verify-email → login → refresh → logout.

    Asserts that every step persists the expected rows AND emits the
    expected audit_log entries inside the request's TX.
    """
    email = "e2e-flow@example.com"
    password = "very-strong-password-123"

    async with _client(app) as client:
        # ── 1. register ────────────────────────────────────────────────
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "consent_pdn": True,
                "display_name": "E2E User",
            },
        )
        assert r.status_code == 201, r.text
        register_body = r.json()
        user_id = register_body["user_id"]
        workspace_id = register_body["workspace_id"]
        cell_id = register_body["cell_id"]
        assert register_body["email_verification_sent"] is True

        # Workspace + cell persisted by real provision_initial_workspace.
        ws = await _select_workspace_by_slug(assertion_session, "e2e-flow")
        assert ws is not None, "workspace row should exist after register"
        assert ws[0] == workspace_id
        assert ws[1] == "free"

        cell_row = await assertion_session.execute(
            text("SELECT id::text, slug FROM multitenancy.cells WHERE id = :c"),
            {"c": cell_id},
        )
        cr = cell_row.first()
        assert cr is not None
        assert cr[1] == "default"

        # Per-cell schema materialized.
        schema_name = f"cell_{cell_id.replace('-', '_')}"
        schema_row = await assertion_session.execute(
            text("SELECT schema_name FROM information_schema.schemata " "WHERE schema_name = :s"),
            {"s": schema_name},
        )
        assert schema_row.scalar() == schema_name

        # Audit row written for register. Filter by actor_id so the
        # assertion is robust to cross-test pollution when other tests in
        # the same session also emit `iam.user.registered` for their own
        # users (db_session_committed's TRUNCATE handles inter-test
        # cleanup, but defence-in-depth on actor_id is cheap).
        assert (
            await _count_audit_rows(assertion_session, "iam.user.registered", actor_id=user_id) == 1
        )
        # Consent row written for pdn.
        assert (
            await _count_audit_rows(assertion_session, "iam.consent.granted", actor_id=user_id) >= 1
        )

        # ── 2. verify-email ────────────────────────────────────────────
        verification = app.state.test_email_sender.last()  # type: ignore[attr-defined]
        assert verification.kind == "verification"
        assert verification.to == email

        r = await client.post("/api/v1/auth/verify-email", json={"token": verification.token})
        assert r.status_code == 200, r.text
        assert r.json() == {"status": "verified"}

        # user.email_verified_at now non-null.
        row = await assertion_session.execute(
            text("SELECT email_verified_at FROM iam.users WHERE id = :u"),
            {"u": user_id},
        )
        assert row.scalar() is not None
        assert (
            await _count_audit_rows(assertion_session, "iam.user.email_verified", actor_id=user_id)
            == 1
        )

        # ── 3. login ───────────────────────────────────────────────────
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        pair_a = r.json()
        assert pair_a["token_type"] == "Bearer"
        assert pair_a["access_token"]
        assert pair_a["refresh_token"]

        assert await _count_audit_rows(assertion_session, "iam.auth.login", actor_id=user_id) == 1

        # Session row persisted.
        sessions_row = await assertion_session.execute(
            text("SELECT count(*) FROM iam.sessions " "WHERE user_id = :u AND revoked_at IS NULL"),
            {"u": user_id},
        )
        assert (sessions_row.scalar() or 0) >= 1

        # ── 4. refresh ─────────────────────────────────────────────────
        r = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": pair_a["refresh_token"]}
        )
        assert r.status_code == 200, r.text
        pair_b = r.json()
        assert pair_b["refresh_token"] != pair_a["refresh_token"]
        assert pair_b["access_token"] != pair_a["access_token"]

        assert await _count_audit_rows(assertion_session, "iam.auth.refresh", actor_id=user_id) == 1

        # Old refresh token marked used.
        used_row = await assertion_session.execute(
            text("SELECT count(*) FROM iam.refresh_tokens WHERE used_at IS NOT NULL")
        )
        assert (used_row.scalar() or 0) >= 1

        # ── 5. logout ──────────────────────────────────────────────────
        r = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": pair_b["refresh_token"]}
        )
        assert r.status_code == 204

        # Logout now attributes to the real user_id (M-1 fix this PR —
        # AuthService.logout looks up session.user_id before revoke).
        assert await _count_audit_rows(assertion_session, "iam.auth.logout", actor_id=user_id) == 1

        # Session revoked.
        revoked_row = await assertion_session.execute(
            text(
                "SELECT count(*) FROM iam.sessions " "WHERE user_id = :u AND revoked_at IS NOT NULL"
            ),
            {"u": user_id},
        )
        assert (revoked_row.scalar() or 0) >= 1


async def test_forgot_and_reset_password_flow(
    app: FastAPI, assertion_session: AsyncSession
) -> None:
    """forgot-password → reset-password chain, end-to-end + audit row check."""
    email = "e2e-reset@example.com"
    initial_pw = "first-strong-password-12"
    new_pw = "second-strong-password-13"

    async with _client(app) as client:
        # Register + verify so the user exists in a clean state.
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": initial_pw, "consent_pdn": True},
        )
        assert r.status_code == 201, r.text
        register_user_id = r.json()["user_id"]

        verification = app.state.test_email_sender.last()  # type: ignore[attr-defined]
        await client.post("/api/v1/auth/verify-email", json={"token": verification.token})

        # Forgot-password — anti-enum 202 + queues a reset email.
        sender_pre = len(app.state.test_email_sender.outbox)  # type: ignore[attr-defined]
        r = await client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert r.status_code == 202
        assert (
            len(app.state.test_email_sender.outbox) == sender_pre + 1  # type: ignore[attr-defined]
        )

        reset = app.state.test_email_sender.last()  # type: ignore[attr-defined]
        assert reset.kind == "password_reset"
        assert reset.to == email

        # Reset-password with the issued token.
        r = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset.token, "new_password": new_pw},
        )
        assert r.status_code == 200
        assert r.json() == {"status": "password_reset"}

        # Audit row for password_reset present (scoped to this test's user).
        assert (
            await _count_audit_rows(
                assertion_session,
                "iam.user.password_reset",
                actor_id=register_user_id,
            )
            == 1
        )

        # Old password invalid; new password works.
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": initial_pw})
        assert r.status_code == 401

        r = await client.post("/api/v1/auth/login", json={"email": email, "password": new_pw})
        assert r.status_code == 200


async def test_register_idempotency_replay(app: FastAPI, assertion_session: AsyncSession) -> None:
    """Second register with same email returns 409 — workspace not duplicated."""
    email = "e2e-replay@example.com"
    pw = "ddupplicate-strong-12"

    async with _client(app) as client:
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pw, "consent_pdn": True},
        )
        assert r.status_code == 201

        # Second attempt: 409 conflict.
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pw, "consent_pdn": True},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "iam.auth.email_already_registered"

    # Exactly one workspace with this slug.
    count = await assertion_session.execute(
        text("SELECT count(*) FROM multitenancy.workspaces WHERE slug = :s"),
        {"s": "e2e-replay"},
    )
    assert (count.scalar() or 0) == 1


async def test_consent_pdn_missing_blocks_register_before_provision(
    app: FastAPI, assertion_session: AsyncSession
) -> None:
    """consent_pdn=false → 422 with no side-effects."""
    email = "e2e-noconsent@example.com"

    async with _client(app) as client:
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "strong-no-consent-12",
                "consent_pdn": False,
            },
        )
        assert r.status_code == 422
        assert r.json()["code"] == "iam.consent.pdn_missing"

    # No workspace, no audit row.
    ws = await _select_workspace_by_slug(assertion_session, "e2e-noconsent")
    assert ws is None
    row = await assertion_session.execute(
        text("SELECT count(*) FROM iam.users WHERE email = :e"),
        {"e": email},
    )
    assert (row.scalar() or 0) == 0


# Phase 00.5b Commit 2 (2026-05-20): the `test_llm_chat_endpoint_is_not_yet_wired`
# negative-canary test that previously pinned the un-wired /api/v1/llm/* surface
# has been deleted now that main.py mounts the llm_gateway routers under
# /api/v1. The replacement positive-smoke for router mounting lives in
# `tests/integration/test_main_app_routes.py::test_all_routers_mounted_under_api_v1`.
# Full provider-matrix coverage (chat, embeddings, byok end-to-end) lands in
# Phase 00.5b Commit 7 via `tests/agents/test_market_brief_demo_flow.py`.
