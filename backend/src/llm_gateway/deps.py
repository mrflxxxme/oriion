"""FastAPI dependency factories for llm_gateway.

The lifespan handler in `src.main` constructs the LLMRouter + KMS + provider
matrix once at startup and stashes the instances on ``app.state``. These
factories read from request-scoped ``app.state`` (via the FastAPI ``Request``)
so per-request handlers can be lean.

Tests can either:
    1. Trigger lifespan via ``asgi_lifespan.LifespanManager(app)`` so the
       real construction path runs (preferred for E2E integration).
    2. Override the factory directly via ``app.dependency_overrides`` —
       avoids needing the lifespan at all (the pattern used by
       `tests/integration/test_e2e_auth_flow.py::app`).

Wave 0 byok_service is a module of free functions (per
``src.llm_gateway.services.byok_service``), not a class — the
``get_byok_service`` factory therefore returns the module itself so
callers can ``byok_service.store_byok_key(...)`` etc. Wave 1+ may
promote it to a class if statefulness arrives.
"""

from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from src.llm_gateway.services import byok_service as _byok_service_module

if TYPE_CHECKING:
    from src.llm_gateway.services.kms_provider import KMSProvider
    from src.llm_gateway.services.router_service import LLMRouter


def _require_state(request: Request, attr: str) -> object:
    """Pull an attribute off ``request.app.state`` or 503 if lifespan didn't run.

    Returning 503 (rather than 500) gives the founder a clear signal: the
    process started but the lifespan boot-path didn't populate state. This
    most commonly happens in test contexts that forgot to wrap the app
    with `LifespanManager` AND forgot to add a ``dependency_overrides``
    entry — that's a wiring bug, not a runtime fault.
    """
    value = getattr(request.app.state, attr, None)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"llm_gateway.{attr} is not on app.state. Lifespan startup "
                "did not run, or a test forgot to override the dependency. "
                "See src/llm_gateway/deps.py for guidance."
            ),
        )
    return value


def get_llm_router(request: Request) -> LLMRouter:
    """Return the process-wide ``LLMRouter`` instance (lifespan-built)."""
    return _require_state(request, "llm_router")  # type: ignore[return-value]


def get_kms_provider(request: Request) -> KMSProvider:
    """Return the active ``KMSProvider`` (LocalAESKMS or YandexKMS)."""
    return _require_state(request, "kms_provider")  # type: ignore[return-value]


def get_byok_service() -> ModuleType:
    """Return the ``byok_service`` module reference.

    Wave 0 byok_service is a flat module of async functions
    (``store_byok_key``, ``get_byok_key_plaintext``, ``list_active_keys``,
    ``revoke_byok_key``). Returning the module lets handlers do
    ``await byok_service.store_byok_key(...)`` while keeping the DI seam
    intact for testing (override the factory to inject a fake module).
    """
    return _byok_service_module
