"""POST /api/v1/auth/* — 8 endpoints conforming to contracts/iam/api.yaml."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from src.iam.deps import get_auth_service, get_magic_link_service
from src.iam.schemas import (
    ForgotPasswordRequest,
    LoginCommand,
    LoginRequest,
    LoginTotpRequest,
    LogoutRequest,
    MagicLinkConsumeRequest,
    MagicLinkRequest,
    RefreshRequest,
    RegisterCommand,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPair,
    TotpChallenge,
    VerifyEmailRequest,
)
from src.iam.services.auth_service import AuthService
from src.iam.services.magic_link_service import MagicLinkService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(req: Request) -> str | None:
    if req.client is None:
        return None
    return req.client.host


def _user_agent(req: Request) -> str | None:
    return req.headers.get("user-agent")


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    result = await service.register(
        RegisterCommand(
            email=payload.email,
            password=payload.password,
            consent_pdn=payload.consent_pdn,
            consent_marketing=payload.consent_marketing,
            display_name=payload.display_name,
            locale=payload.locale,
            ip=_client_ip(request),
            user_agent=_user_agent(request),
        )
    )
    return RegisterResponse(
        user_id=result.user_id,
        workspace_id=result.workspace_id,
        cell_id=result.cell_id,
        email=result.email,
        email_verification_sent=result.email_verification_sent,
    )


@router.post("/login", response_model=TokenPair | TotpChallenge)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair | TotpChallenge:
    """Password login. Returns a token pair, OR a 2FA challenge (HTTP 200 with
    ``two_factor_required: true``) when the account has active TOTP — the client
    then completes login via POST /auth/login/totp."""
    return await service.login(
        LoginCommand(
            email=payload.email,
            password=payload.password,
            ip=_client_ip(request),
            user_agent=_user_agent(request),
        )
    )


@router.post("/login/totp", response_model=TokenPair)
async def login_totp(
    payload: LoginTotpRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    """Second leg of 2FA login — exchange the challenge token + TOTP/backup code
    for a token pair."""
    return await service.login_totp(
        challenge_token=payload.challenge_token,
        code=payload.code,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )


@router.post("/magic-link/request", status_code=status.HTTP_202_ACCEPTED)
async def magic_link_request(
    payload: MagicLinkRequest,
    request: Request,
    service: MagicLinkService = Depends(get_magic_link_service),
) -> Response:
    """Anti-enum: always 202 regardless of email existence."""
    await service.request(payload.email, ip=_client_ip(request), user_agent=_user_agent(request))
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/magic-link/consume", response_model=TokenPair)
async def magic_link_consume(
    payload: MagicLinkConsumeRequest,
    request: Request,
    service: MagicLinkService = Depends(get_magic_link_service),
) -> TokenPair:
    """Consume a single-use magic-link token → issue a session/token pair."""
    return await service.consume(
        payload.token, ip=_client_ip(request), user_agent=_user_agent(request)
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return await service.rotate_refresh(
        payload.refresh_token,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    await service.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    payload: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await service.verify_email(payload.token)
    return {"status": "verified"}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
)
async def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    """Anti-enum: always 202 regardless of email existence."""
    await service.resend_verification(
        payload.email, ip=_client_ip(request), user_agent=_user_agent(request)
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    """Anti-enum: always 202 regardless of email existence."""
    await service.forgot_password(
        payload.email, ip=_client_ip(request), user_agent=_user_agent(request)
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    payload: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await service.reset_password(payload.token, payload.new_password)
    return {"status": "password_reset"}
