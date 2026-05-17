"""Seed dev DB с sample workspace + cell + admin user (idempotent).

Phase 00.1 — placeholder skeleton. Реальный seed-flow появится в Phase 00.3
после Cell/Workspace/User schema. Сейчас скрипт verifies connectivity и
выходит без действий (idempotent no-op), чтобы make dev-bootstrap completed.

Запуск:

    uv run python scripts/seed_dev_data.py
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/seed_dev_data.py

Exits 0 если успех, 1 если DB unreachable.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from typing import TYPE_CHECKING, Final
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_DSN_CRED_PATTERN: Final[re.Pattern[str]] = re.compile(r"://[^@/\s:]+:[^@/\s]+@")


def _redact(message: str) -> str:
    """Replace credentials in DSN-style URLs внутри error messages."""
    return _DSN_CRED_PATTERN.sub("://***:***@", message)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

DEV_ADMIN_EMAIL: Final[str] = "admin@oriion.local"
DEFAULT_DATABASE_URL: Final[str] = (
    "postgresql+asyncpg://oriion:oriion-dev@localhost:5432/oriion_dev"
)


async def seed_dev_admin(session: AsyncSession) -> UUID:
    """Создать dev admin user. Returns user_id (existing или new).

    Phase 00.1 placeholder — domain schema появится в Phase 00.3,
    поэтому реализация возвращает stub UUID без записи в DB.
    """
    _ = session  # placeholder: будет использоваться в Phase 00.3
    return uuid4()


async def seed_dev_workspace(session: AsyncSession, owner_id: UUID) -> UUID:
    """Создать dev workspace + initial cell. Returns workspace_id.

    Phase 00.1 placeholder — реальный seed в Phase 00.3.
    """
    _ = (session, owner_id)
    return uuid4()


async def _main_async() -> int:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

    engine = create_async_engine(database_url, echo=False, future=True)
    try:
        # Verify connectivity + pgvector + extensions
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            result = await conn.execute(
                text(
                    "SELECT extname FROM pg_extension WHERE extname IN "
                    "('vector', 'pg_trgm', 'unaccent') ORDER BY extname"
                )
            )
            extensions = sorted(row[0] for row in result.fetchall())
            sys.stdout.write(f"✓ DB connected. Extensions installed: {extensions}\n")

            if "vector" not in extensions:
                sys.stderr.write(
                    "✗ pgvector extension не установлен. "
                    "Проверь infra/postgres/init-pgvector.sh + перезапусти "
                    "postgres volume (`make clean && make dev`).\n"
                )
                return 1
    except Exception as exc:  # noqa: BLE001 — broad для startup diagnostics
        sys.stderr.write(
            f"✗ DB seed failed: {type(exc).__name__}: {_redact(str(exc))}\n"
        )
        return 1
    finally:
        await engine.dispose()

    sys.stdout.write(
        "✓ Dev seed placeholder run successfully. "
        "Domain seed (workspace + cell + admin) returns в Phase 00.3.\n"
    )
    return 0


def main() -> int:
    """Idempotent seed workflow.

    Phase 00.1: verify DB connectivity + pgvector presence. Domain seed Phase 00.3.
    """
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
