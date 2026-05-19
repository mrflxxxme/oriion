"""POST /api/v1/llm/embeddings — Wave 0 stub (DI wiring lands Phase 00.5)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.llm_gateway.schemas import EmbeddingRequest, ErrorResponse

router = APIRouter(prefix="/llm", tags=["inference"])


@router.post(
    "/embeddings",
    responses={
        200: {"description": "OK"},
        501: {"model": ErrorResponse, "description": "Runtime wiring pending (Wave 0)"},
    },
)
async def embeddings(payload: EmbeddingRequest) -> JSONResponse:
    """Wave 0 stub — provider DI lands Phase 00.5."""
    _ = payload
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            code="llm_gateway.runtime_pending",
            message="Embedding DI wiring lands Phase 00.5; "
            "service layer is unit-tested directly.",
            details={"request_id": str(uuid.uuid4())},
        ).model_dump(),
    )
