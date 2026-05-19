"""Pydantic 2.x schemas for multitenancy — matches contracts/multitenancy/api.yaml 1:1.

Field names + required-sets match the OpenAPI document. Deviations require
a contract extension (architect-PR).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Workspace ─────────────────────────────────────────────────────────────


PlanTier = Literal["free", "starter", "pro", "enterprise"]


class WorkspaceCreate(BaseModel):
    """POST /workspaces body."""

    model_config = ConfigDict(extra="forbid")

    slug: str | None = None
    display_name: str
    billing_email: EmailStr | None = None
    plan_tier: PlanTier = "free"


class WorkspaceOut(BaseModel):
    """Public workspace projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    display_name: str
    billing_email: EmailStr | None = None
    country_code: str
    timezone: str
    plan_tier: PlanTier
    created_at: datetime
    updated_at: datetime


class WorkspacePage(BaseModel):
    items: list[WorkspaceOut]
    next_cursor: str | None = None


# ── Cell ──────────────────────────────────────────────────────────────────


class CellCreate(BaseModel):
    """POST /workspaces/{workspace_id}/cells body."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    display_name: str
    vertical_template_slug: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class CellOut(BaseModel):
    """Public cell projection.

    Note: the SQLAlchemy column is `settings_jsonb`; the API field is
    `settings`. Conversion happens via a property in the service layer
    (we don't use `from_attributes=True` for this projection — services
    construct it explicitly).
    """

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    workspace_id: UUID
    slug: str
    display_name: str
    vertical_template_slug: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class CellPage(BaseModel):
    items: list[CellOut]
    next_cursor: str | None = None


# ── CellMember ────────────────────────────────────────────────────────────


class CellMemberOut(BaseModel):
    """Public cell-member projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cell_id: UUID
    user_id: UUID
    role_id: UUID
    joined_at: datetime
    invited_by: UUID | None = None
    last_active_at: datetime | None = None


# ── Invitation ────────────────────────────────────────────────────────────


class InvitationCreate(BaseModel):
    """POST /cells/{cell_id}/members/invite body."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role_id: UUID


class InvitationOut(BaseModel):
    """Invitation projection.

    The Wave 0 backend does NOT yet materialize a sibling `invitations`
    table (the api.yaml shape is forward-declared per contract README
    "not modelled in this schema.sql to keep the W0 surface tight"). The
    router synthesizes an InvitationOut shape from the immediate INSERT
    of a CellMember row (a Wave-0 simplification — see services note).
    """

    id: UUID
    cell_id: UUID
    email: EmailStr
    role_id: UUID
    expires_at: datetime
    created_at: datetime
