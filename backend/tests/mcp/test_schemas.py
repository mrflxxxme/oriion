"""Unit: Pydantic round-trip for mcp schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.mcp.schemas import MCPConnectionCreate, MCPConnectionOut


def test_create_minimal_payload() -> None:
    cmd = MCPConnectionCreate(
        workspace_id=uuid4(),
        name="brave-search",
        server_type="http",
        endpoint="https://example.test/mcp",
    )
    assert cmd.cell_id is None
    assert cmd.is_active is True
    assert cmd.capabilities == {}


def test_create_rejects_bad_server_type() -> None:
    with pytest.raises(ValidationError):
        MCPConnectionCreate(
            workspace_id=uuid4(),
            name="weird",
            server_type="websocket",  # type: ignore[arg-type]
            endpoint="ws://example.test/",
        )


def test_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        MCPConnectionCreate(
            workspace_id=uuid4(),
            name="",
            server_type="http",
            endpoint="https://example.test/",
        )


def test_create_rejects_extra_fields() -> None:
    """`extra='forbid'` keeps the command shape contract-stable."""
    with pytest.raises(ValidationError):
        MCPConnectionCreate.model_validate(
            {
                "workspace_id": str(uuid4()),
                "name": "x",
                "server_type": "http",
                "endpoint": "https://example.test/",
                "rogue_field": True,
            }
        )


def test_out_from_attributes_roundtrip() -> None:
    """`from_attributes=True` lets us hydrate from SQLAlchemy rows directly."""

    class FakeRow:
        def __init__(self) -> None:
            self.id = uuid4()
            self.workspace_id = uuid4()
            self.cell_id: object = None
            self.name = "brave-search"
            self.server_type = "http"
            self.endpoint = "https://example.test/mcp"
            self.capabilities: dict[str, object] = {"tools": []}
            self.is_active = True
            self.created_at = datetime.now(UTC)
            self.updated_at = datetime.now(UTC)

    out = MCPConnectionOut.model_validate(FakeRow())
    assert out.name == "brave-search"
    assert out.server_type == "http"
    # Round-trip through JSON to assert serialiser shape.
    j = out.model_dump_json()
    assert "brave-search" in j
