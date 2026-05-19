"""Pytest fixtures для backend tests.

Phase 00.1 — минимальные fixtures для smoke tests. Domain fixtures (auth,
multi-tenancy cells, etc.) будут добавлены в Phase 00.2+.

Integration tests требующие живой docker-compose стек — помечать
``@pytest.mark.integration``. Запуск:

    pytest -m integration          # только integration
    pytest -m "not integration"    # только unit (default в CI smoke job)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


TEST_DB_URL: str = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://oriion:oriion-dev@localhost:5432/oriion_test",
)


@pytest_asyncio.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Async SQLAlchemy engine для test DB — function-scoped.

    Used only by integration tests. Unit tests должны мокать DAL.

    Note (2026-05-19): function-scoped (not session-scoped) so the engine
    lives within the same event loop as the test that consumes it. Session-
    scoped pytest-asyncio fixtures install a separate loop from each
    function's loop, and asyncpg's Future bookkeeping refuses to cross
    loops ("attached to a different loop"). Cost is one connect/dispose
    cycle per integration test — acceptable given the limited integration
    test count in Wave 0; testcontainers session reuse arrives in 00.2.5.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test AsyncSession backed by a fresh connection + outer TX rollback.

    Implementation note (2026-05-19): the previous session-only impl re-used
    the connection across tests and left it in an aborted state when a test
    triggered an expected EXCEPTION (e.g. append-only trigger fires).
    Subsequent tests then failed with
        cannot use Connection.transaction() in a manually started transaction
    The savepoint-rollback pattern below isolates each test in its own
    connection so a botched TX state cannot leak. See audit Section 04
    (Test Adequacy) flag for the rationale.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    async with db_engine.connect() as conn:
        # Outer transaction — rolled back wholesale at fixture teardown so the
        # DB state stays clean between tests even when the test itself committed
        # or raised mid-transaction.
        outer_tx = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            if outer_tx.is_active:
                await outer_tx.rollback()


@pytest.fixture(scope="session")
def backend_version() -> str:
    """Pinned backend package version — assertable в smoke tests."""
    import src

    return src.__version__
