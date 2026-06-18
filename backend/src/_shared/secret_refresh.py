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


async def refresh_app_secrets(app: FastAPI) -> Settings:
    """Re-read secrets (Lockbox) + rebuild secret-derived ``app.state`` — no restart.

    The Lockbox fetch + Settings parse is blocking, so it runs in a worker thread
    to keep the event loop responsive; the (synchronous, in-memory) provider
    rebuild then swaps ``app.state`` atomically from the caller's coroutine.
    """
    settings = await asyncio.to_thread(reload_settings)
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
