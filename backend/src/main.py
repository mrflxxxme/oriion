"""FastAPI application entrypoint.

Phase 00.1: skeleton /health.
Phase 00.2: wires iam routers (auth + me) under /api/v1 prefix +
            RFC 7807 problem+json exception handler for IamError.
"""

from __future__ import annotations

from typing import Final

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import __version__
from src._shared.logging import configure_structlog
from src.iam.exceptions import IamError, RateLimitExceeded
from src.iam.routers.auth import router as auth_router
from src.iam.routers.me import router as me_router

API_TITLE: Final[str] = "TEAMLY_RU Backend"
API_DESCRIPTION: Final[str] = (
    "Cloud-платформа AI-команд для СМБ + personal-users сегмента РФ. "
    "Phase 00.2 — Custom JWT auth (iam bounded context) wired under /api/v1."
)


class HealthResponse(BaseModel):
    status: str
    version: str


configure_structlog()

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)

# ── routes ────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")


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
