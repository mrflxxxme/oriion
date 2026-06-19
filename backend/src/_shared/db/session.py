"""Async SQLAlchemy engine + session factory + FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src._shared.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Process-wide AsyncEngine. Lazy-constructed; cached."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=5,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Process-wide session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an AsyncSession.

    Usage::

        @router.get("/...")
        async def handler(db: AsyncSession = Depends(get_db)) -> ...:
            ...
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
