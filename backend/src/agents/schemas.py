"""Pydantic schemas for agents bounded context.

Mirrors contracts/agents/api.yaml. Wave 0 surface is read-mostly:
list archetypes (system catalog), list cell-instances, provision team.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentArchetypeOut(BaseModel):
    """System-level AI persona, exposed via GET /api/v1/agent-archetypes."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    vertical_slug: str
    display_name: str
    role_category: str
    prompt_version: str
    model_provider_slug: str
    model_name: str
    model_fallback: str | None
    tools_allowed: list[str]
    is_active: bool
    status: str


class AgentInstanceOut(BaseModel):
    """Cell-scoped agent instance."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cell_id: UUID
    agent_archetype_id: UUID
    custom_name: str | None
    custom_settings_jsonb: dict[str, Any] = Field(default_factory=dict)
    total_tasks_completed: int
    last_used_at: datetime | None
    created_at: datetime
    archived_at: datetime | None


class TeamPresetOut(BaseModel):
    """Provisioning recipe — archetype bundle for fast cell bootstrap."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vertical_slug: str
    slug: str
    display_name: str
    description: str
    archetype_ids: list[UUID]
    default_workflow_dag_json: dict[str, Any] = Field(default_factory=dict)


class TeamProvisionRequest(BaseModel):
    """POST /api/v1/cells/{cell_id}/teams payload."""

    preset_key: str = Field(..., description="team_preset.slug to provision")


class TeamProvisionResponse(BaseModel):
    """POST /api/v1/cells/{cell_id}/teams response."""

    team_preset_id: UUID
    cell_id: UUID
    agent_instances: list[AgentInstanceOut]
