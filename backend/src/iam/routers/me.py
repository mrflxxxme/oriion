"""GET/PATCH /api/v1/users/me — authenticated profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.iam.deps import get_auth_service
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.iam.schemas import UserPatch, UserResponse
from src.iam.services.auth_service import AuthService

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
