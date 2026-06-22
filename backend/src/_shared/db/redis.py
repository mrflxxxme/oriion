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
    """Process-wide Redis client. Lazy-constructed; cached.

    Safe for the long-lived web tier (one event loop for the process lifetime).
    NOT safe for the Dramatiq worker, which runs ``asyncio.run()`` per message
    (fresh loop each) — a cached client binds connections to the first loop and
    raises ``Event loop is closed`` on the 2nd message. Worker code uses
    ``build_redis_client()`` instead.
    """
    return _new_redis_client()


def build_redis_client() -> Redis:
    """A FRESH (non-cached) async Redis client bound to the caller's current
    event loop. Use from the Dramatiq worker's per-message ``asyncio.run`` so the
    client is created + closed within the same loop (mirrors the per-message
    engine in ``runtime.queue.actor._run_dispatch``)."""
    return _new_redis_client()


def _new_redis_client() -> Redis:
    settings = get_settings()
    client = Redis.from_url(
        settings.redis_url.get_secret_value(),
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )
    return cast(Redis, client)


async def get_redis() -> Redis:
    """FastAPI dependency yielding the shared Redis client."""
    return get_redis_client()
