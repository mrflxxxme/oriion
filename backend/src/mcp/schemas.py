"""Pydantic 2.x schemas for mcp.

Wave 0 surfaces:
    * `MCPConnectionCreate` — service-layer command (Wave 0 internal — no
      router exposes it yet per AC8 / Phase 00.4 § Task 14).
    * `MCPConnectionOut` — read model.

These mirror `mcp.mcp_connections` (Wave 0 minimal DDL). Full API contract
(contracts/mcp/api.yaml) is SKELETON status — pre-public; Wave 2 hardening
will introduce request/response shapes for the eventual /api/mcp/* endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Wave 0 transports per migration CHECK constraint. SSE / websocket
# deferred to Wave 2 (per ADR-013 — full MCP protocol surface).
MCPServerType = Literal["stdio", "http"]


class MCPConnectionCreate(BaseModel):
    """Internal command — `MCPConnectionService.create` input."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    cell_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    server_type: MCPServerType
    endpoint: str = Field(
        min_length=1,
        description=(
            "URL (http transport) or shell command line (stdio transport). "
            "Validation is transport-aware Wave 1+."
        ),
    )
    capabilities: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class MCPConnectionOut(BaseModel):
    """Read model for `mcp.mcp_connections` rows."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    cell_id: UUID | None
    name: str
    server_type: MCPServerType
    endpoint: str
    capabilities: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
