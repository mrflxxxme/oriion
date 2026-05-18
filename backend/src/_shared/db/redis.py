"""Async Redis singleton + FastAPI dependency.

Uses `redis.asyncio.Redis` (redis-py 5.x). The client maintains its own
connection pool internally; one instance per process is sufficient.
"""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from redis.asyncio import Redis

from src._shared.config import get_settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Process-wide Redis client. Lazy-constructed; cached."""
    settings = get_settings()
    client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )
    return cast(Redis, client)


async def get_redis() -> Redis:
    """FastAPI dependency yielding the shared Redis client."""
    return get_redis_client()
