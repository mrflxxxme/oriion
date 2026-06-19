"""No-redeploy secret refresh (AC-W1-9).

Rebuilds the secret-derived application state (KMS provider + LLM provider matrix
+ LLMRouter, all on ``app.state``) from a freshly-read ``Settings``. Because
``reload_settings()`` re-runs the Lockbox settings source, this picks up a
**rotated Lockbox secret version without a redeploy / restart**.

Trigger: a ``SIGHUP`` handler registered at startup (Unix only) — an operator (or
the rotation tooling) sends ``SIGHUP`` after bumping the Lockbox version and the
running process re-reads + re-wires its provider clients. ``apply_secret_state``
is also the single source of truth for the *initial* lifespan build, so startup
and refresh can never drift.
"""

from __future__ import annotations

import asyncio
import base64
import os
import secrets
import signal
from typing import TYPE_CHECKING

import structlog

from src._shared.config import Settings, reload_settings
from src.llm_gateway.factory import build_llm_router
from src.llm_gateway.services.kms_provider import KMSProvider, LocalAESKMS, YandexKMS

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = structlog.get_logger(__name__)


def resolve_master_key_bytes(settings: Settings) -> bytes:
    """Resolve the LocalAESKMS master key bytes from Settings.

    Precedence: ``settings.byok_master_key_b64`` → env ``BYOK_MASTER_KEY_B64``
    (legacy) → dev/test ephemeral key (loud warning). Prod with no key fails fast.
    Audit M3 closure: prod paths come through Settings (or Lockbox-populated env).
    """
    b64 = settings.byok_master_key_b64.get_secret_value() if settings.byok_master_key_b64 else ""
    if not b64:
        b64 = os.environ.get("BYOK_MASTER_KEY_B64", "")
    if b64:
        return base64.b64decode(b64)

    if settings.is_prod:
        raise RuntimeError(
            "BYOK_MASTER_KEY_B64 is empty in prod. Set the env-var (or Settings "
            "field, or the YC Lockbox payload) to a base64-encoded 32-byte AES-256 "
            "key. See ADR-014 §1."
        )
    logger.warning(
        "kms.master_key.ephemeral",
        msg=(
            "BYOK_MASTER_KEY_B64 is empty — generating an ephemeral dev key. "
            "BYOK keys encrypted in this process cannot be decrypted after restart."
        ),
        app_env=settings.app_env,
    )
    return secrets.token_bytes(32)


def _build_kms(settings: Settings) -> KMSProvider:
    if settings.kms_backend == "yandex":
        return YandexKMS()
    return LocalAESKMS(master_key=resolve_master_key_bytes(settings))


def apply_secret_state(app: FastAPI, settings: Settings) -> None:
    """(Re)build KMS + LLM providers/router from ``settings`` and swap them onto
    ``app.state``. The single construction path shared by lifespan startup AND
    the live refresh, so the two can never drift in provider matrix / KMS."""
    kms_provider = _build_kms(settings)
    providers, circuits, llm_router = build_llm_router(settings)
    app.state.settings = settings
    app.state.kms_provider = kms_provider
    app.state.llm_providers = providers
    app.state.llm_circuits = circuits
    app.state.llm_router = llm_router


async def _reset_db_redis_caches() -> None:
    """Drop the process-wide engine / sessionmaker / redis ``lru_cache``s so the
    next access rebuilds from the rotated ``DATABASE_URL`` / ``REDIS_URL`` (AC-W1-9).

    Without this, ``get_engine()`` / ``get_redis_client()`` keep the
    pre-rotation DSN until a full restart — a SIGHUP refresh would otherwise
    rebuild only KMS + LLM providers while DB/Redis stay on the old (possibly
    compromised) credentials. The live engine/client are disposed before the
    cache is cleared so the old connection pool is not leaked.
    """
    from src._shared.db.redis import get_redis_client
    from src._shared.db.session import get_engine, get_session_maker

    # Grab the live objects, then clear the caches FIRST so any concurrent caller
    # immediately rebuilds from the rotated DSN — never handed a sessionmaker bound
    # to an already-disposed engine. Dispose the old objects AFTER: their in-flight
    # checked-out connections finish naturally, idle pool conns close on dispose.
    old_engine = get_engine() if get_engine.cache_info().currsize else None
    old_redis = get_redis_client() if get_redis_client.cache_info().currsize else None
    get_session_maker.cache_clear()
    get_engine.cache_clear()
    get_redis_client.cache_clear()
    if old_engine is not None:
        await old_engine.dispose()
    if old_redis is not None:
        await old_redis.aclose()


async def refresh_app_secrets(app: FastAPI) -> Settings:
    """Re-read secrets (Lockbox) + rebuild secret-derived ``app.state`` — no restart.

    The Lockbox fetch + Settings parse is blocking, so it runs in a worker thread
    to keep the event loop responsive; the (synchronous, in-memory) provider
    rebuild then swaps ``app.state`` atomically from the caller's coroutine. The
    DB/Redis caches are dropped too so a rotated DATABASE_URL/REDIS_URL is applied
    in-process, not just KMS + LLM (AC-W1-9).
    """
    settings = await asyncio.to_thread(reload_settings)
    await _reset_db_redis_caches()
    apply_secret_state(app, settings)
    logger.info(
        "shared.secret_refresh.applied",
        kms_backend=settings.kms_backend,
        provider_slugs=list(app.state.llm_providers.keys()),
        lockbox=bool(settings.lockbox_secret_id),
    )
    return settings


def register_sighup_refresh(app: FastAPI, loop: asyncio.AbstractEventLoop) -> bool:
    """Register ``SIGHUP`` → ``refresh_app_secrets`` on ``loop`` (Unix only).

    Returns True if the handler was registered, False where ``SIGHUP`` or
    ``loop.add_signal_handler`` is unavailable (Windows / non-main thread / some
    event loops) — in which case rotation falls back to a rolling restart.
    """
    sighup = getattr(signal, "SIGHUP", None)
    if sighup is None:
        return False
    try:
        loop.add_signal_handler(
            sighup, lambda: asyncio.ensure_future(refresh_app_secrets(app), loop=loop)
        )
    except (NotImplementedError, RuntimeError, ValueError):
        return False
    logger.info("shared.secret_refresh.sighup_registered")
    return True
