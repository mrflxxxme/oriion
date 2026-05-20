"""Pydantic schemas for tasks bounded context."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: str = ""
    prompt: str = Field(..., min_length=1, description="User prompt for the Coordinator")
    parent_task_id: UUID | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cell_id: UUID
    parent_task_id: UUID | None
    agent_instance_id: UUID | None
    initiated_by_user_id: UUID
    title: str
    description: str
    status: str
    priority: int
    started_at: datetime | None
    completed_at: datetime | None
    total_cost_credits: Decimal
    total_input_tokens: int
    total_output_tokens: int
    created_at: datetime


class TaskStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    step_index: int
    agent_archetype_id: UUID
    step_type: str
    status: str
    cost_credits: Decimal
    started_at: datetime | None
    completed_at: datetime | None
    input_jsonb: dict[str, Any] = Field(default_factory=dict)
    output_jsonb: dict[str, Any] = Field(default_factory=dict)


class TaskArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    step_id: UUID | None
    artifact_type: str
    storage_kind: str
    mime_type: str
    byte_size: int
    content_hash_sha256: str
    content_inline: dict[str, Any] | None = None
    created_at: datetime
