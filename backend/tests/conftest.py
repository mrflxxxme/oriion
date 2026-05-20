"""Backend pytest fixtures.

Phase 00.2.5 (2026-05-19) — promoted from "function-scoped engine bound
to TEST_DATABASE_URL env" to a session-scoped testcontainers PG fixture:

* ``pg_container`` (session, sync): boots ``pgvector/pgvector:pg16`` once per
  pytest run (unless ``TEST_DATABASE_URL`` is preset — then CI's existing
  GitHub service container path is used unchanged).
* ``test_db_url`` (session): the asyncpg DSN exposed by the container or
  the env override.
* ``_bootstrap_db`` (session, lazy): runs ``CREATE EXTENSION vector +
  pg_trgm + unaccent`` then ``alembic upgrade heads`` once at session start.
  Mirrors the per-job steps in ``.github/workflows/ci-backend.yml`` so the
  local + CI surfaces stay 1-to-1. NOT autouse — only triggered when a
  test requests ``db_engine`` (which transitively pulls it in). Unit-only
  runs (default addopts ``-m "not integration"``) never spin up the
  container.
* ``db_engine`` (function): async SQLAlchemy engine derived from
  ``test_db_url``. Stays function-scoped despite the session container
  because asyncpg refuses to reuse a connection across event loops
  ("Future attached to a different loop"). pytest-asyncio installs a
  fresh loop per test (``asyncio_default_fixture_loop_scope = "function"``);
  reusing a session-scoped engine would crash on every second test that
  consumed it. The container itself is the expensive part to provision —
  the engine create/dispose cycle is ~10ms.
* ``db_session`` (function): SAVEPOINT-rollback pattern inside one
  connection pulled from ``db_engine``. Default for ~95% of integration
  tests — fast, isolated, no cross-test bleed. The outer TX is rolled
  back wholesale at teardown so even tests that raised mid-transaction
  cannot leak state.
* ``db_session_committed`` (function): for tests marked
  ``@pytest.mark.commit_required`` — runs against a fresh connection in
  auto-commit mode. Each statement COMMITs immediately so BEFORE-COMMIT
  triggers fire, partition routing executes, and replication semantics
  are honoured. Teardown TRUNCATEs every non-system table touchable by
  ``oriion_app`` (modulo the ``alembic_version`` table) so the next test
  starts from a clean schema. Use this fixture only for tests that
  specifically assert cross-TX or trigger-after-COMMIT behaviour — it's
  noticeably slower (~150ms cleanup) than the default SAVEPOINT pattern.

Markers:
* ``integration`` — needs the real PG container (deselected by default
  addopts; selected via ``-m integration``).
* ``commit_required`` — needs ``db_session_committed`` instead of
  ``db_session`` because the test asserts behaviour that only manifests
  after a real COMMIT.
* ``live`` — hits real LLM provider APIs (declared, currently unused;
  reserved for Phase 00.6).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from testcontainers.postgres import PostgresContainer


# ── PG container (session-scoped) ────────────────────────────────────────


def _env_test_db_url() -> str | None:
    """Return the preset CI / dev test DSN if any, else None.

    When ``TEST_DATABASE_URL`` is set we trust the caller (CI service
    container, devcontainer, founder's local stack) and skip the
    testcontainers spin-up. This keeps the CI 8-min budget unchanged
    until the team explicitly opts into testcontainers in CI as well.
    """
    return os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer | None]:
    """Session-scoped pgvector/pgvector:pg16 container.

    Yields ``None`` when ``TEST_DATABASE_URL`` is preset — the env DSN
    takes precedence and the container is not started.
    """
    if _env_test_db_url():
        yield None
        return

    # Imported lazily so unit-only test runs (which deselect 'integration'
    # via default addopts) never trigger Docker discovery.
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer(
        image="pgvector/pgvector:pg16",
        username="oriion",
        password="oriion-dev",
        dbname="oriion_test",
        driver="asyncpg",
    )
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def test_db_url(pg_container: PostgresContainer | None) -> str:
    """Async PG DSN — from env override OR testcontainers container."""
    env_url = _env_test_db_url()
    if env_url:
        return env_url

    assert pg_container is not None  # guaranteed by branch above
    # testcontainers returns the URL with the driver embedded
    # (postgresql+asyncpg://oriion:oriion-dev@host:port/oriion_test).
    url: str = pg_container.get_connection_url()
    return url


# ── DB bootstrap (session-scoped, autouse) ───────────────────────────────


@pytest.fixture(scope="session")
def _bootstrap_db(test_db_url: str) -> None:
    """Apply CREATE EXTENSION + ``alembic upgrade heads`` once per session.

    No-op when ``TEST_DATABASE_URL`` is preset AND the caller signals
    "already migrated" via ``TEST_DB_SKIP_BOOTSTRAP=1`` (default in CI
    where the workflow runs its own ``alembic upgrade heads`` step prior
    to ``pytest`` invocation — re-running here would be wasted work).
    """
    if os.environ.get("TEST_DB_SKIP_BOOTSTRAP") == "1":
        return

    # Sync DSN for psycopg + alembic — strip "+asyncpg" driver.
    sync_url = test_db_url.replace("+asyncpg", "")

    _create_extensions(sync_url)
    _alembic_upgrade_heads(sync_url)


def _create_extensions(sync_url: str) -> None:
    """Mirror .github/workflows/ci-backend.yml:84-90 — extensions before
    alembic so vector column types and other extension-dependent DDL
    resolve cleanly during migration.
    """
    import psycopg

    with psycopg.connect(sync_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")


def _alembic_upgrade_heads(sync_url: str) -> None:
    """Run Alembic against the test container as if it were prod.

    Uses ``heads`` (plural) — the migration graph has 8 heads (_shared,
    iam, multitenancy, rbac, audit, llm_gateway, billing, mcp).
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    # env.py reads DATABASE_URL from the environment (intentionally —
    # protection against running migrations against a hardcoded localhost
    # if env is misconfigured). Promote `sync_url` back to async driver
    # form so `async_engine_from_config` in env.py works.
    async_url = (
        sync_url
        if "+asyncpg" in sync_url
        else sync_url.replace("postgresql://", "postgresql+asyncpg://")
    )
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = async_url

    try:
        # Pre-create alembic_version with VARCHAR(255). Mirrors
        # .github/workflows/ci-backend.yml:99-111 workaround for the
        # alembic.ini cp1251 issue documented in HANDOFF.md:120.
        import psycopg

        with psycopg.connect(sync_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "  version_num VARCHAR(255) NOT NULL"
                "    CONSTRAINT alembic_version_pkc PRIMARY KEY"
                ")"
            )

        # Resolve alembic.ini relative to the backend package root regardless
        # of where pytest is invoked from.
        backend_root = Path(__file__).resolve().parent.parent
        ini_path = backend_root / "alembic.ini"
        cfg = Config(str(ini_path))
        cfg.set_main_option("script_location", str(backend_root / "migrations"))
        # NOTE: do NOT set `path_separator` programmatically here. alembic
        # 1.16+ would also use it to split `version_locations`, which is
        # space-separated in alembic.ini (12 bounded-context subdirs) —
        # forcing `os` collapses them to one bogus path and `upgrade` runs
        # as a no-op. The DeprecationWarning is silenced via pyproject
        # `filterwarnings` until Phase 00.6 rewrites alembic.ini with the
        # `path_separator` option.

        command.upgrade(cfg, "heads")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev


# ── Async engine + session (function-scoped) ─────────────────────────────


@pytest_asyncio.fixture
async def db_engine(
    test_db_url: str,
    _bootstrap_db: None,  # dependency triggers schema setup lazily
) -> AsyncIterator[AsyncEngine]:
    """Async SQLAlchemy engine bound to the session-scoped PG container.

    Function-scoped despite the session container because asyncpg refuses
    to share a connection across event loops; pytest-asyncio installs a
    fresh loop per test under the default ``loop_scope="function"``.

    Reusing the engine across tests would crash with
        Future attached to a different loop
    on the second test that consumed it. The container itself is the
    expensive part of the setup (~3-8s docker pull on cold start, ~100ms
    on warm); the engine create/dispose cycle is ~10ms.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(test_db_url, echo=False, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test AsyncSession backed by SAVEPOINT-rollback isolation.

    Pattern: open a fresh connection, BEGIN an outer transaction, hand
    the session back to the test. The test may COMMIT / RELEASE inside —
    those happen at the SAVEPOINT level, not the outer TX. At teardown
    the outer TX is rolled back wholesale, wiping every change the test
    made (including those it "committed").

    Trade-off: tests asserting behaviour that requires a real COMMIT
    (cross-session visibility, BEFORE-COMMIT triggers that fire only on
    real commit, partition routing observation from a second session)
    should use ``db_session_committed`` via the ``commit_required``
    marker instead.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    async with db_engine.connect() as conn:
        outer_tx = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            if outer_tx.is_active:
                await outer_tx.rollback()


@pytest_asyncio.fixture
async def db_session_committed(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """AsyncSession that uses real COMMITs + TRUNCATE-based cleanup.

    Use via ``@pytest.mark.commit_required`` on tests that need real
    cross-TX semantics — E2E TestClient flows, audit_log partition
    observation from a fresh session, RLS-context-across-COMMIT replays.

    Cleanup strategy: at teardown, TRUNCATE every table in the
    application schemas (iam, multitenancy, rbac, audit, llm_gateway,
    billing, mcp) CASCADE. The ``audit.audit_log`` partitioned table is
    handled specially — TRUNCATE on the parent cascades to children
    (Postgres 16). System tables (``alembic_version``, extensions,
    role grants) stay intact so the next test starts on the same
    migrated schema.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncSession(bind=db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        # TRUNCATE every transactional table in our application schemas.
        # Run outside of any TX so this always succeeds even if the test
        # left state aborted.
        #
        # IMPORTANT exclusions:
        # * `alembic_version` — migrations metadata, never reset
        # * `rbac.{permissions, system_roles, role_permissions}` — seeded
        #   by migration `migrations/versions/rbac/0005_seed_built_in_roles.py`;
        #   wiping them breaks tests/rbac/test_seed_data.py + any test
        #   that LEFT JOINs from cell_members.role_id.
        #
        # Per-cell schemas (`cell_<uuid>`) are NOT in the schemaname filter
        # below — they're created on-demand by `provision_cell_schema` and
        # disappear with the testcontainers container at session end.
        async with db_engine.begin() as conn:
            tables = await conn.execute(
                text(
                    "SELECT schemaname || '.' || tablename "
                    "  FROM pg_tables "
                    " WHERE schemaname IN ('iam','multitenancy','rbac',"
                    "                       'audit','llm_gateway','billing','mcp') "
                    "   AND tablename NOT LIKE 'alembic_%' "
                    "   AND NOT (schemaname = 'rbac' AND tablename IN "
                    "            ('permissions','system_roles','role_permissions'))"
                )
            )
            qualified = [row[0] for row in tables.all()]
            if qualified:
                # CASCADE handles FK + partition children in one shot.
                await conn.execute(
                    text(f"TRUNCATE TABLE {', '.join(qualified)} RESTART IDENTITY CASCADE")
                )


# ── Misc ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def backend_version() -> str:
    """Pinned backend package version — assertable in smoke tests."""
    import src

    return src.__version__


# ── Pydantic-AI canned model fixture (T3 mock pattern) ──────────────────


@pytest.fixture
def pydantic_ai_test_model():
    """Build a ``FakeLLMGatewayModel`` pre-loaded with the «Market & content
    brief» scenario canned responses.

    Returns a single shared instance — tests that need multiple model
    instances (one per role) call ``model.set_response(...)`` themselves
    or instantiate ``FakeLLMGatewayModel`` directly. The fixture seeds the
    default scenario so the common case ``model.set_scenario(...)`` +
    ``Agent(model=model)`` works out of the box.

    Per founder-resolved T3 (2026-05-20): NOT pydantic_ai's TestModel;
    canned ``ModelResponse`` lists keyed by ``(role_key, scenario_id)``;
    fail-loud on unknown key.
    """
    from tests._fixtures.canned_pydantic_ai import FakeLLMGatewayModel
    from tests._fixtures.canned_pydantic_ai.market_brief_demo import (
        RESPONSES,
        SCENARIO_ID,
    )

    # Default role_key — tests can override per-role by constructing a
    # second instance via FakeLLMGatewayModel("researcher") etc.
    model = FakeLLMGatewayModel(role_key="coordinator")
    for (role_key, scenario_id), responses in RESPONSES.items():
        model.set_response(role_key, scenario_id, responses)
    model.set_scenario(SCENARIO_ID)
    return model
