"""Alembic env — async migrations runner for TEAMLY_RU multi-version directory.

Phase 00.1: skeleton env.py. Реальный target_metadata подключается в Phase 00.3
когда появятся domain models.

Multi-version operation per ADR-024:
- Каждый bounded context имеет свой versions/<context>/ subdirectory
- alembic.ini `version_locations` enumerates active context directories
- Migrations создаются с branch labels: `alembic revision --branch-label iam`
"""

from __future__ import annotations

import asyncio
import configparser
import os
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

config = context.config

# Force UTF-8 read of alembic.ini. Python's configparser (and Alembic's
# memoized Config.file_config) default to locale.getencoding(), which on
# Windows ru-RU is cp1251 — non-ASCII commentary inside alembic.ini blows up
# with UnicodeDecodeError. We shadow Alembic's memoized_property by pre-
# loading alembic.ini with explicit encoding="utf-8" and writing the parsed
# instance directly into config.__dict__, sidestepping the lazy descriptor.
# logging.config.fileConfig (Python 3.10+) accepts an encoding kwarg of its
# own, so the logger section is loaded with the same encoding contract.
if config.config_file_name is not None:
    _here = os.path.abspath(os.path.dirname(config.config_file_name))
    _utf8_parser = configparser.ConfigParser({"here": _here})
    with open(config.config_file_name, encoding="utf-8") as _ini_f:
        _utf8_parser.read_file(_ini_f)
    config.__dict__["file_config"] = _utf8_parser
    fileConfig(config.config_file_name, encoding="utf-8")

# Phase 00.3 entry-point: импортировать MetaData всех bounded contexts.
# Пока target_metadata = None, autogenerate disabled до появления models.
target_metadata = None

# Require DATABASE_URL env-var (alembic.ini sqlalchemy.url оставлен пустым
# интенционально — защита от запуска migrations против hardcoded localhost
# когда environment не настроен).
_env_url = os.environ.get("DATABASE_URL")
if not _env_url:
    raise RuntimeError(
        "DATABASE_URL не установлен. Alembic требует явный connection string "
        "через env-var. Для local dev: `export DATABASE_URL=postgresql+asyncpg://...` "
        "или используй `make dev` который запустит compose stack."
    )
config.set_main_option("sqlalchemy.url", _env_url)


def run_migrations_offline() -> None:
    """Run migrations в offline mode (emit SQL без подключения)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations с AsyncEngine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations против target DB."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
