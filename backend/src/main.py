"""FastAPI application entrypoint.

Phase 00.1 — minimum viable app для AC6 healthcheck (compose up → healthy).
Реальные routes/middleware/auth добавляются в Phase 00.2+.
"""

from __future__ import annotations

from typing import Final

from fastapi import FastAPI
from pydantic import BaseModel

from src import __version__

API_TITLE: Final[str] = "TEAMLY_RU Backend"
API_DESCRIPTION: Final[str] = (
    "Cloud-платформа AI-команд для СМБ + personal-users сегмента РФ. "
    "Phase 00.1 skeleton — /health endpoint only."
)


class HealthResponse(BaseModel):
    """Health-check payload."""

    status: str
    version: str


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    """Liveness probe. Используется docker-compose healthcheck (AC6) и Phase 00.6 staging."""
    return HealthResponse(status="ok", version=__version__)
