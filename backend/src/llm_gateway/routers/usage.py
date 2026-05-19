"""GET /api/v1/llm/usage — aggregated usage for the current workspace.

Wave 0 stub — DI wiring + tenant-context lands Phase 00.5; the underlying
``llm_usage_log`` aggregation queries are straightforward but routing
through workspace-scoped RLS requires the full request context which is
populated later. Service-layer aggregation utilities are not exposed Wave 0;
add when the route is wired.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from src.llm_gateway.schemas import ErrorResponse

router = APIRouter(prefix="/llm", tags=["usage"])


@router.get(
    "/usage",
    responses={
        200: {"description": "OK"},
        501: {"model": ErrorResponse, "description": "Runtime wiring pending (Wave 0)"},
    },
)
async def usage(
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    group_by: str | None = Query(default=None),
) -> JSONResponse:
    _ = (from_, to, group_by)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            code="llm_gateway.runtime_pending",
            message="Usage aggregation DI lands Phase 00.5.",
        ).model_dump(),
    )
