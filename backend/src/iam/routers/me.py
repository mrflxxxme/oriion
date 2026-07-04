"""GET/PATCH /api/v1/users/me — authenticated profile endpoints.

Phase 01.8 adds authenticated 2FA management (/users/me/totp/*) and the
session-list backend (/users/me/sessions) here, since all require the
Bearer-authenticated current user.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.iam.deps import get_auth_service, get_totp_service
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.iam.schemas import (
    SessionListResponse,
    TotpConfirmRequest,
    TotpConfirmResponse,
    TotpDisableRequest,
    TotpEnrollResponse,
    UserPatch,
    UserResponse,
)
from src.iam.services.auth_service import AuthService
from src.iam.services.totp_service import TotpService

router = APIRouter(prefix="/users", tags=["profile"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    auth: AuthenticatedUser = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(auth.user)


@router.patch("/me", response_model=UserResponse)
async def patch_me(
    payload: UserPatch,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return await service.update_user_profile(
        auth.user.id,
        display_name=payload.display_name,
        locale=payload.locale,
        timezone=payload.timezone,
    )


# ── 2FA / TOTP management (Phase 01.8) ────────────────────────────────────


@router.post("/me/totp/enroll", response_model=TotpEnrollResponse)
async def totp_enroll(
    auth: AuthenticatedUser = Depends(get_current_user),
    service: TotpService = Depends(get_totp_service),
) -> TotpEnrollResponse:
    """Begin 2FA enrollment — returns the base32 secret + otpauth provisioning
    URI (shown once). Credential is PENDING until /totp/confirm."""
    enrollment = await service.enroll(user_id=auth.user.id, account_label=auth.user.email)
    return TotpEnrollResponse(
        secret=enrollment.secret, provisioning_uri=enrollment.provisioning_uri
    )


@router.post("/me/totp/confirm", response_model=TotpConfirmResponse)
async def totp_confirm(
    payload: TotpConfirmRequest,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: TotpService = Depends(get_totp_service),
) -> TotpConfirmResponse:
    """Activate 2FA after proving possession with a live code. Returns
    single-use backup codes (shown once)."""
    backup_codes = await service.confirm(user_id=auth.user.id, code=payload.code)
    return TotpConfirmResponse(backup_codes=backup_codes)


@router.post("/me/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def totp_disable(
    payload: TotpDisableRequest,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: TotpService = Depends(get_totp_service),
) -> Response:
    """Disable 2FA — requires a valid current code or backup code."""
    await service.disable(user_id=auth.user.id, code=payload.code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── session list / revoke (Phase 01.8) ────────────────────────────────────


@router.get("/me/sessions", response_model=SessionListResponse)
async def list_sessions(
    auth: AuthenticatedUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SessionListResponse:
    """List the current user's active sessions (device/UA/timestamps), flagging
    the caller's own session. RLS-equivalent scoping: only the user's rows."""
    sessions = await service.list_sessions(auth.user.id, current_session_id=auth.claims.sid)
    return SessionListResponse(sessions=sessions)


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    auth: AuthenticatedUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> Response:
    """Revoke one of the current user's own sessions. A session that does not
    belong to the caller yields 404 (no cross-user existence oracle)."""
    await service.revoke_session(auth.user.id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_other_sessions(
    auth: AuthenticatedUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> Response:
    """Log out everywhere except the caller's current session."""
    await service.revoke_all_other_sessions(auth.user.id, keep_session_id=auth.claims.sid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
