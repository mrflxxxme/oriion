"""Worker per-message SSE/redis lifecycle (fix for the asyncio-loop-bound redis
client bug — see memory `teamly-worker-asyncio-loop-redis-finding`).

The Dramatiq worker runs ``asyncio.run()`` per message (fresh loop each). The DB
engine is already rebuilt per message; the redis SSE publisher must be too, else
the 2nd dispatched message reuses a client bound to the closed first loop and
raises ``Event loop is closed``. These tests pin the two enabling pieces:
``build_sse_publisher`` is non-caching, and ``RedisSSEPublisher.aclose`` releases
the lazily-created publish client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from src.runtime.redis_sse_publisher import RedisSSEPublisher
from src.runtime.sse_publisher import (
    InProcessSSEPublisher,
    build_sse_publisher,
    get_sse_publisher,
    reset_sse_publisher_for_tests,
)


def test_build_sse_publisher_returns_fresh_instances() -> None:
    """Worker path: a fresh publisher per call (per-loop redis client)."""
    a = build_sse_publisher()
    b = build_sse_publisher()
    assert a is not b
    assert isinstance(a, InProcessSSEPublisher)  # default test backend


def test_get_sse_publisher_is_cached_singleton() -> None:
    """Web tier (one long-lived loop): the cached singleton is fine."""
    reset_sse_publisher_for_tests()
    assert get_sse_publisher() is get_sse_publisher()


@pytest.mark.asyncio
async def test_redis_publisher_aclose_releases_lazy_client() -> None:
    pub = RedisSSEPublisher(redis_url="redis://localhost:6379/0")
    fake = AsyncMock()
    pub._shared_client = fake  # simulate a client lazily created on first publish
    await pub.aclose()
    fake.aclose.assert_awaited_once()
    assert pub._shared_client is None


@pytest.mark.asyncio
async def test_redis_publisher_aclose_noop_for_injected_client() -> None:
    """An injected client (tests) is owned by the caller — aclose must not close it."""
    fake = AsyncMock()
    pub = RedisSSEPublisher(client=fake)
    await pub.aclose()
    fake.aclose.assert_not_called()
