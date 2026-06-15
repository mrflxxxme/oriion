"""FastAPI application entrypoint.

Phase 00.1: skeleton /health.
Phase 00.2: wires iam routers (auth + me) under /api/v1 prefix +
            RFC 7807 problem+json exception handler for IamError.
Phase 00.5b (Commit 2): full router-wiring overhaul:
    * multitenancy routers (workspaces, cells, workspace_cells)
    * llm_gateway routers (chat, embeddings, byok, providers, usage)
    * exception handlers for MultitenancyError + LLMGatewayException + MCPError
    * lifespan provider DI (DeepSeek + YandexGPT + GigaChat + LocalAESKMS + LLMRouter)
    * mcp router include is deferred — Wave 0 mcp is framework-only per ADR-013;
      a public mcp/tools HTTP surface lands in Wave 1+.
"""

from __future__ import annotations

import base64
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import __version__
from src._shared.config import Settings, get_settings
from src._shared.logging import configure_structlog
from src._shared.observability import register_default_metrics, setup_otel, shutdown_otel
from src.agents.exceptions import AgentsError
from src.agents.routers.archetypes import router as archetypes_router
from src.agents.routers.instances import router as agent_instances_router
from src.agents.routers.teams import router as teams_router
from src.iam.exceptions import IamError, RateLimitExceeded
from src.iam.routers.auth import router as auth_router
from src.iam.routers.me import router as me_router
from src.llm_gateway.circuit_breaker import ProviderCircuit
from src.llm_gateway.exceptions import LLMGatewayException
from src.llm_gateway.providers.base import LLMProvider
from src.llm_gateway.providers.deepseek import DeepSeekProvider
from src.llm_gateway.providers.gigachat import GigaChatProvider
from src.llm_gateway.providers.yandex import YandexGPTProvider
from src.llm_gateway.routers.byok import router as byok_router
from src.llm_gateway.routers.chat import router as chat_router
from src.llm_gateway.routers.embeddings import router as embeddings_router
from src.llm_gateway.routers.providers import router as providers_router
from src.llm_gateway.routers.usage import router as usage_router
from src.llm_gateway.services.kms_provider import KMSProvider, LocalAESKMS, YandexKMS
from src.llm_gateway.services.router_service import LLMRouter
from src.mcp.exceptions import MCPError, ToolRateLimitExceeded
from src.multitenancy.exceptions import MultitenancyError
from src.multitenancy.routers.cells import router as cells_router
from src.multitenancy.routers.cells import workspace_cells_router
from src.multitenancy.routers.workspaces import router as workspaces_router
from src.tasks.exceptions import TasksError
from src.tasks.routers.stream import router as task_stream_router
from src.tasks.routers.tasks import router as tasks_router

API_TITLE: Final[str] = "TEAMLY_RU Backend"
API_DESCRIPTION: Final[str] = (
    "Cloud-платформа AI-команд для СМБ + personal-users сегмента РФ. "
    "Phase 00.5b — iam + multitenancy + llm_gateway routers wired under /api/v1."
)

_logger = structlog.get_logger(__name__)

configure_structlog()


class HealthResponse(BaseModel):
    status: str
    version: str


# ── lifespan: provider DI + KMS + LLMRouter construction ──────────────────


def _resolve_master_key_bytes(settings: Settings) -> bytes:
    """Resolve the LocalAESKMS master key bytes from Settings.

    Precedence:
        1. settings.byok_master_key_b64 (non-empty SecretStr)
        2. env BYOK_MASTER_KEY_B64 (legacy path — kept for back-compat
           with deployments that haven't migrated to Settings yet)
        3. dev/test only: generate an ephemeral 32-byte key + emit a loud
           warning. NEVER use in prod — startup fails fast instead.

    Audit M3 closure: prod paths must come through Settings; this resolver
    surfaces empty-config as an explicit error rather than silently
    booting a broken KMS.
    """
    b64 = settings.byok_master_key_b64.get_secret_value() if settings.byok_master_key_b64 else ""
    if not b64:
        b64 = os.environ.get("BYOK_MASTER_KEY_B64", "")
    if b64:
        return base64.b64decode(b64)

    if settings.is_prod:
        raise RuntimeError(
            "BYOK_MASTER_KEY_B64 is empty in prod. Set the env-var (or Settings "
            "field) to a base64-encoded 32-byte AES-256 key. See ADR-014 §1."
        )
    _logger.warning(
        "kms.master_key.ephemeral",
        msg=(
            "BYOK_MASTER_KEY_B64 is empty — generating an ephemeral dev key. "
            "BYOK keys encrypted in this process cannot be decrypted after "
            "restart. Set BYOK_MASTER_KEY_B64 for stable dev encryption."
        ),
        app_env=settings.app_env,
    )
    return secrets.token_bytes(32)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the LLM provider matrix + KMS + LLMRouter once at startup.

    All instances are stashed on ``app.state`` for the llm_gateway.deps.py
    DI factories to read. Tests can either:
        1. Trigger lifespan via ``asgi_lifespan.LifespanManager(app)``, or
        2. Override DI factories directly via ``dependency_overrides``.

    See `tests/integration/test_e2e_auth_flow.py::app` for the override-only
    pattern (no provider/KMS state needed since those tests don't hit
    llm_gateway endpoints).
    """
    settings = get_settings()

    # ── Observability (Phase 00.6 Commit 4) ──────────────────────────────
    # Setup OpenTelemetry BEFORE provider construction so outbound httpx
    # calls (DeepSeek/YandexGPT/GigaChat) are auto-instrumented from the
    # very first request. setup_otel is idempotent + feature-gated via
    # Settings.otel_traces_enabled — unit tests with in-memory exporters can
    # short-circuit cleanly.
    setup_otel(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        enabled=settings.otel_traces_enabled,
    )
    # FastAPI instrumentation needs the app object; safe to call after
    # FastAPI() construction. The instrumentor handles "already instrumented"
    # idempotently when lifespan re-enters in tests.
    if settings.otel_traces_enabled:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    # Prometheus metrics — register defaults + assert all 9 metrics present.
    # /metrics endpoint mounted ниже в module-level code (after app
    # construction). Phase 00.6 ships REGISTRATION ONLY; per-callsite
    # instrumentation в orchestrator/router_service is Wave-1 AC-W1-2.
    register_default_metrics()

    # ── KMS provider ─────────────────────────────────────────────────────
    kms_provider: KMSProvider
    if settings.kms_backend == "yandex":
        kms_provider = YandexKMS()
    else:
        master_key = _resolve_master_key_bytes(settings)
        kms_provider = LocalAESKMS(master_key=master_key)

    # ── LLM providers ────────────────────────────────────────────────────
    # Providers are constructed with whatever credentials Settings holds.
    # An empty credential just means calls to that provider's HTTP API will
    # fail at request-time — the lifespan boot stays green so routers like
    # /api/v1/llm/providers (health probe) can still answer.
    # The provider classes implement the LLMProvider Protocol structurally
    # (they don't inherit from it). mypy --strict in dict-assignment context
    # doesn't auto-narrow concrete -> Protocol, so cast() is the explicit
    # acknowledgement that we've verified the shape matches at the Protocol
    # boundary in tests/llm_gateway/test_provider_*_mock.py.
    providers: dict[str, LLMProvider] = {}
    provider_timeout = settings.llm_provider_timeout_seconds
    providers["deepseek"] = cast(
        LLMProvider,
        DeepSeekProvider(
            api_key=settings.deepseek_api_key.get_secret_value(),
            timeout_seconds=provider_timeout,
        ),
    )
    providers["yandexgpt"] = cast(
        LLMProvider,
        YandexGPTProvider(
            iam_token=settings.yandex_iam_token.get_secret_value(),
            catalog_id=settings.yandex_catalog_id,
            timeout_seconds=provider_timeout,
        ),
    )
    providers["gigachat"] = cast(
        LLMProvider,
        GigaChatProvider(
            auth_key=settings.gigachat_auth_key.get_secret_value(),
            timeout_seconds=provider_timeout,
        ),
    )
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    llm_router = LLMRouter(providers=providers, circuits=circuits)

    # Stash everything on app.state — llm_gateway.deps reads from here.
    app.state.settings = settings
    app.state.kms_provider = kms_provider
    app.state.llm_providers = providers
    app.state.llm_circuits = circuits
    app.state.llm_router = llm_router

    _logger.info(
        "lifespan.startup.complete",
        kms_backend=settings.kms_backend,
        provider_slugs=list(providers.keys()),
    )

    try:
        yield
    finally:
        _logger.info("lifespan.shutdown")
        shutdown_otel()


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Prometheus /metrics — mounted at module-level так что endpoint доступен
# даже когда lifespan ещё не отработал (e.g. health-probe от docker compose
# в первые секунды до register_default_metrics). The ASGI app reads from
# the global REGISTRY which has all 9 metrics registered at import-time
# (Counter/Gauge/Histogram constructors run on metrics.py import).
from prometheus_client import make_asgi_app  # noqa: E402

app.mount("/metrics", make_asgi_app())


# ── routes ────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.get("/healthz", response_model=HealthResponse, tags=["meta"])
async def healthz() -> HealthResponse:
    """Kubernetes-style liveness probe alias. Used by docker-compose
    healthcheck + Caddy upstream health-check per Phase 00.6 spec."""
    return HealthResponse(status="ok", version=__version__)


# iam (Phase 00.2)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")

# multitenancy (Phase 00.5b Commit 2 wiring)
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(cells_router, prefix="/api/v1")
app.include_router(workspace_cells_router, prefix="/api/v1")

# llm_gateway (Phase 00.5b Commit 2 wiring)
app.include_router(chat_router, prefix="/api/v1")
app.include_router(embeddings_router, prefix="/api/v1")
app.include_router(byok_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")

# agents (Phase 00.5b Commit 5 wiring)
app.include_router(archetypes_router, prefix="/api/v1")
app.include_router(agent_instances_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")

# tasks (Phase 00.5b Commit 6 wiring)
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(task_stream_router, prefix="/api/v1")

# mcp: Wave 0 is framework-only per ADR-013; no public HTTP surface yet.
# A `mcp/routers/tools.py` router lands in Wave 1+ when real MCP servers
# ship — see backend/src/mcp/__init__.py docstring.


# ── exception handler → RFC 7807 application/problem+json ─────────────────


@app.exception_handler(IamError)
async def iam_error_handler(request: Request, exc: IamError) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://oriion.app/errors/{exc.code.replace('.', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "code": exc.code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    body["instance"] = str(request.url)

    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitExceeded):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
        headers=headers or None,
    )


@app.exception_handler(TasksError)
async def tasks_error_handler(request: Request, exc: TasksError) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://oriion.app/errors/{exc.code.replace('.', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "code": exc.code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    body["instance"] = str(request.url)
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )


@app.exception_handler(AgentsError)
async def agents_error_handler(request: Request, exc: AgentsError) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://oriion.app/errors/{exc.code.replace('.', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "code": exc.code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    body["instance"] = str(request.url)
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )


@app.exception_handler(MultitenancyError)
async def multitenancy_error_handler(request: Request, exc: MultitenancyError) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://oriion.app/errors/{exc.code.replace('.', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "code": exc.code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    body["instance"] = str(request.url)
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )


@app.exception_handler(MCPError)
async def mcp_error_handler(request: Request, exc: MCPError) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://oriion.app/errors/{exc.code.replace('.', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "code": exc.code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    body["instance"] = str(request.url)

    headers: dict[str, str] = {}
    if isinstance(exc, ToolRateLimitExceeded):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
        headers=headers or None,
    )


# LLMGatewayException has no per-class status_code (unlike iam/multitenancy/mcp
# bases) — code is the discriminator and the HTTP status is encoded by the
# specific subclass through the FastAPI handler chain below. We pick the
# default 502 for the un-classified base + override per known subclass.
_LLM_GATEWAY_STATUS: dict[str, int] = {
    "llm_gateway.provider_unavailable": 502,
    "llm_gateway.budget_exceeded": 402,
    "llm_gateway.byok_key_invalid": 400,
    "llm_gateway.byok_key_not_found": 404,
    "llm_gateway.kms_error": 500,
    "llm_gateway.circuit_open": 503,
    "llm_gateway.lifespan_not_ready": 503,
    "llm_gateway.unknown": 502,
}
_LLM_GATEWAY_TITLES: dict[str, str] = {
    "llm_gateway.provider_unavailable": "All LLM providers unavailable",
    "llm_gateway.budget_exceeded": "LLM budget exceeded",
    "llm_gateway.byok_key_invalid": "BYOK key invalid",
    "llm_gateway.byok_key_not_found": "BYOK key not found",
    "llm_gateway.kms_error": "KMS operation failed",
    "llm_gateway.circuit_open": "LLM provider circuit open",
    "llm_gateway.lifespan_not_ready": "LLM gateway not initialized",
    "llm_gateway.unknown": "LLM gateway error",
}


@app.exception_handler(LLMGatewayException)
async def llm_gateway_error_handler(request: Request, exc: LLMGatewayException) -> JSONResponse:
    code = exc.code
    status_code = _LLM_GATEWAY_STATUS.get(code, 502)
    title = _LLM_GATEWAY_TITLES.get(code, "LLM gateway error")
    body: dict[str, object] = {
        "type": f"https://oriion.app/errors/{code.replace('.', '-')}",
        "title": title,
        "status": status_code,
        "code": code,
    }
    if exc.message and exc.message != code:
        body["detail"] = exc.message
    body["instance"] = str(request.url)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )
