"""Wait for Postgres + Redis readiness during dev/CI startup.

Используется в `make dev-bootstrap` после `docker compose up -d` чтобы блокировать
seed-step до полной готовности dependencies. Также вызывается из CI workflows
backend и frontend перед integration-тестами.

Запуск:

    uv run python scripts/wait_for_db.py
    # с переопределёнными timeout/DSN:
    DATABASE_URL=postgresql+asyncpg://... REDIS_URL=redis://... \
        uv run python scripts/wait_for_db.py

Exits с кодом 0 если оба services ready, 1 если timeout превышен.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Final
from urllib.parse import urlparse

import asyncpg
import redis.asyncio as redis_async

DEFAULT_TIMEOUT: Final[int] = 60
POLL_INTERVAL: Final[float] = 1.0
DEFAULT_DATABASE_URL: Final[str] = (
    "postgresql+asyncpg://oriion:oriion-dev@localhost:5432/oriion_dev"
)
DEFAULT_REDIS_URL: Final[str] = "redis://localhost:6379/0"


def _to_asyncpg_dsn(sqlalchemy_url: str) -> str:
    """Преобразовать SQLAlchemy URL (``postgresql+asyncpg://``) → asyncpg DSN.

    asyncpg ожидает голый ``postgresql://`` без SQLAlchemy driver-tag.
    """
    if sqlalchemy_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + sqlalchemy_url[len("postgresql+asyncpg://") :]
    return sqlalchemy_url


async def wait_for_postgres(dsn: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Block until Postgres принимает connections OR timeout exceeded.

    Args:
        dsn: SQLAlchemy-style URL (``postgresql+asyncpg://...``) или native asyncpg DSN.
        timeout: Max seconds to wait.

    Raises:
        TimeoutError: Postgres не ready within timeout.
    """
    native_dsn = _to_asyncpg_dsn(dsn)
    parsed = urlparse(native_dsn)
    target = f"{parsed.hostname}:{parsed.port or 5432}"

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        try:
            conn = await asyncpg.connect(native_dsn, timeout=POLL_INTERVAL * 2)
            await conn.execute("SELECT 1")
            await conn.close()
            sys.stdout.write(f"✓ Postgres ready ({target}) after {attempt} attempts\n")
            return
        except (OSError, asyncpg.PostgresError, asyncio.TimeoutError) as exc:
            last_error = exc
            await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError(
        f"Postgres at {target} not ready within {timeout}s ({attempt} attempts); "
        f"last error: {last_error}"
    )


async def wait_for_redis(url: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Block until Redis отвечает на PING OR timeout exceeded.

    Args:
        url: Redis URL (``redis://host:port/db``).
        timeout: Max seconds to wait.

    Raises:
        TimeoutError: Redis не ready within timeout.
    """
    parsed = urlparse(url)
    target = f"{parsed.hostname}:{parsed.port or 6379}"

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        try:
            client = redis_async.from_url(url, socket_timeout=POLL_INTERVAL * 2)
            try:
                pong = await client.ping()
            finally:
                await client.aclose()
            if pong:
                sys.stdout.write(f"✓ Redis ready ({target}) after {attempt} attempts\n")
                return
        except (OSError, redis_async.RedisError, asyncio.TimeoutError) as exc:
            last_error = exc
            await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError(
        f"Redis at {target} not ready within {timeout}s ({attempt} attempts); "
        f"last error: {last_error}"
    )


async def _main_async() -> int:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    redis_url = os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)
    timeout = int(os.environ.get("WAIT_TIMEOUT", str(DEFAULT_TIMEOUT)))

    try:
        await asyncio.gather(
            wait_for_postgres(database_url, timeout=timeout),
            wait_for_redis(redis_url, timeout=timeout),
        )
    except TimeoutError as exc:
        sys.stderr.write(f"✗ Readiness check failed: {exc}\n")
        return 1
    return 0


def main() -> int:
    """Wait для обоих services используя env DATABASE_URL + REDIS_URL."""
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
