"""Pydantic 2.x schemas for iam — matches contracts/iam/api.yaml 1:1.

Authoritative shape per ADR-024. Field names + required-sets match the
OpenAPI document; deviations require a contract extension (architect-PR).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Auth — requests ───────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """POST /auth/register body.

    Invariant 6: consent_pdn MUST be true; service returns 422 with
    code=iam.consent.pdn_missing otherwise.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str | None = None
    locale: str = "ru-RU"
    consent_pdn: bool = Field(
        description=(
            "FZ-152 personal-data processing consent. MUST be true. "
            "Pinned at grant via consent_version_current."
        ),
    )
    consent_marketing: bool = False


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


class ResendVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str
    new_password: str = Field(min_length=12)


# ── Auth — responses ──────────────────────────────────────────────────────


class RegisterResponse(BaseModel):
    user_id: UUID
    workspace_id: UUID
    cell_id: UUID
    email: EmailStr
    email_verification_sent: bool = True


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = Field(description="Seconds until access_token expiry.")
    token_type: Literal["Bearer"] = "Bearer"


# ── /users/me ─────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    email_verified_at: datetime | None = None
    display_name: str | None = None
    locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = None
    locale: str | None = None
    timezone: str | None = None


# ── Internal — JWT claims ─────────────────────────────────────────────────


class AccessTokenClaims(BaseModel):
    """Decoded HS256 access token. Matches issue_access_token output."""

    sub: UUID
    sid: UUID
    jti: UUID
    iat: int
    exp: int
    iss: str
    aud: str
    type: Literal["access"] = "access"


# ── Internal — command/result records (services use these, not raw kwargs) ─


class RegisterCommand(BaseModel):
    """Internal command consumed by AuthService.register."""

    email: EmailStr
    password: str
    consent_pdn: bool
    consent_marketing: bool = False
    display_name: str | None = None
    locale: str = "ru-RU"
    ip: str | None = None
    user_agent: str | None = None


class RegisterResult(BaseModel):
    """Internal — AuthService.register output (super-set of RegisterResponse)."""

    user_id: UUID
    workspace_id: UUID
    cell_id: UUID
    email: EmailStr
    email_verification_sent: bool


class LoginCommand(BaseModel):
    email: EmailStr
    password: str
    ip: str | None = None
    user_agent: str | None = None
