"""Pydantic 2.x schemas for audit context.

These DTOs are internal-only — audit events are emitted from inside the
backend, never from external HTTP callers. The schemas exist so services
get input validation + a deterministic shape that tests can assert on.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ActorType = Literal["user", "agent", "system"]


class AuditEventCreate(BaseModel):
    """Input DTO for emitting an audit event.

    Mirrors the columns of ``audit.audit_log`` minus ``id`` / ``ts``
    (both DB-generated). ``actor_id`` is required when ``actor_type``
    is ``user`` or ``agent``; system events may carry a synthetic UUID
    (e.g. all-zeros) — enforced by the caller, not this DTO.
    """

    model_config = ConfigDict(extra="forbid")

    actor_type: ActorType
    actor_id: UUID | None = None
    action: str = Field(min_length=1, max_length=255)
    resource_type: str | None = Field(default=None, max_length=255)
    resource_id: UUID | None = None
    cell_id: UUID | None = None
    workspace_id: UUID | None = None
    payload: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None


class AuditEventOut(BaseModel):
    """Output DTO — read-side view of an audit_log row."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    ts: datetime
    actor_type: ActorType
    actor_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: UUID | None
    cell_id: UUID | None
    workspace_id: UUID | None
    payload: dict[str, Any] | None
    ip: str | None
    user_agent: str | None
