"""POST /api/v1/llm/chat/completions — proxy + atomic cost ledger write.

Wave 0 implementation is intentionally a thin handler:
  * Provider instances + circuits are not yet wired into FastAPI DI here
    (DI assembly lands with Phase 00.5 — the user-facing wiring phase per
    the architect-PR plan). For Wave 0 the handler returns a 501 indicating
    the gateway plumbing exists but the runtime wiring is pending.
  * Tests exercise the service layer directly (router_service, billing_service)
    so the route handler is mostly a contract surface.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.llm_gateway.schemas import ChatCompletionRequest, ErrorResponse

router = APIRouter(prefix="/llm", tags=["inference"])


@router.post(
    "/chat/completions",
    responses={
        200: {"description": "OK"},
        501: {"model": ErrorResponse, "description": "Runtime wiring pending (Wave 0)"},
    },
)
async def chat_completion(payload: ChatCompletionRequest) -> JSONResponse:
    """Wave 0 stub — DI wiring lands with Phase 00.5.

    The service-layer plumbing (LLMRouter + record_llm_cost) is fully
    implemented; this handler is the OpenAPI surface that will be wired
    once provider instances are constructed via DI.
    """
    _ = payload  # contract surface — validated by Pydantic, no-op handler
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=ErrorResponse(
            code="llm_gateway.runtime_pending",
            message="Provider DI wiring lands in Phase 00.5; "
            "service layer is unit-tested directly.",
            details={"request_id": str(uuid.uuid4())},
        ).model_dump(),
    )
