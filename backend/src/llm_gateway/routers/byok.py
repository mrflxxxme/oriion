"""POST/GET/DELETE /api/v1/llm/byok-keys — Wave 0 surface.

Service-layer is fully implemented; this router emits the OpenAPI surface
and will be DI-wired in Phase 00.5 (auth + tenant-context + KMS provider).
For Wave 0 we return 501 from the live handler — direct service-layer
tests cover the encryption + fingerprint + cloudevent path.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, Response

from src.llm_gateway.schemas import BYOKKeyCreateRequest, ErrorResponse

router = APIRouter(prefix="/llm", tags=["byok"])


@router.post(
    "/byok-keys",
    responses={
        201: {"description": "Created"},
        501: {"model": ErrorResponse, "description": "Runtime wiring pending (Wave 0)"},
    },
)
async def create_byok_key(payload: BYOKKeyCreateRequest) -> JSONResponse:
    """Wave 0 stub — DI wiring (auth + KMS + tenant context) lands Phase 00.5."""
    _ = payload
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            code="llm_gateway.runtime_pending",
            message="BYOK DI wiring lands Phase 00.5; service layer is unit-tested.",
        ).model_dump(),
    )


@router.get(
    "/byok-keys",
    responses={
        200: {"description": "OK"},
        501: {"model": ErrorResponse, "description": "Runtime wiring pending (Wave 0)"},
    },
)
async def list_byok_keys() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            code="llm_gateway.runtime_pending",
            message="BYOK list wiring lands Phase 00.5.",
        ).model_dump(),
    )


@router.delete(
    "/byok-keys/{byok_key_id}",
    responses={
        204: {"description": "Revoked"},
        501: {"model": ErrorResponse, "description": "Runtime wiring pending (Wave 0)"},
    },
)
async def revoke_byok_key(byok_key_id: UUID) -> Response:
    _ = byok_key_id
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            code="llm_gateway.runtime_pending",
            message="BYOK revoke wiring lands Phase 00.5.",
        ).model_dump(),
    )
