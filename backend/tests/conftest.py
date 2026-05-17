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


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Async SQLAlchemy engine для test DB.

    Используется только integration-тестами. Unit tests должны мокать DAL.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Rolled-back AsyncSession per test.

    Каждый test получает свежую транзакцию, после теста — rollback,
    чтобы test isolation сохранялась без drop/recreate DB.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="session")
def backend_version() -> str:
    """Pinned backend package version — assertable в smoke tests."""
    import src

    return src.__version__
