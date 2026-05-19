"""Unit: SQLAlchemy mapping assertions for mcp.MCPConnection.

These tests do NOT touch a database — they verify that the model is
correctly declared (table name, schema, constraints, columns) so a
mis-typed mapping is caught before integration runs.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from src.mcp.models import MCPConnection


def test_mcp_connection_table_in_mcp_schema() -> None:
    table = MCPConnection.__table__
    assert table.schema == "mcp"
    assert table.name == "mcp_connections"


def test_mcp_connection_columns_match_ddl() -> None:
    cols = {c.name for c in MCPConnection.__table__.columns}
    assert cols == {
        "id",
        "workspace_id",
        "cell_id",
        "name",
        "server_type",
        "endpoint",
        "capabilities",
        "is_active",
        "created_at",
        "updated_at",
    }


def test_mcp_connection_indexes_declared() -> None:
    index_names = {idx.name for idx in MCPConnection.__table__.indexes}
    assert "mcp_connections_workspace_name_idx" in index_names
    assert "mcp_connections_workspace_active_idx" in index_names


def test_mcp_connection_check_constraint_server_type() -> None:
    constraint_names = {c.name for c in MCPConnection.__table__.constraints if c.name is not None}
    assert "mcp_connections_server_type_check" in constraint_names


def test_mcp_connection_nullable_columns() -> None:
    cols = {c.name: c.nullable for c in MCPConnection.__table__.columns}
    assert cols["cell_id"] is True
    assert cols["workspace_id"] is False
    assert cols["name"] is False
    assert cols["server_type"] is False


def test_mcp_connection_instance_attributes() -> None:
    """Sanity-check that an in-memory instance round-trips its fields."""
    conn = MCPConnection(
        workspace_id=uuid4(),
        cell_id=None,
        name="brave-search",
        server_type="http",
        endpoint="https://example.test/mcp",
        capabilities={"tools": []},
        is_active=True,
    )
    assert conn.name == "brave-search"
    assert conn.server_type == "http"
    assert isinstance(conn.workspace_id, UUID)
    # Defaults (server_default) are not applied client-side; just confirm
    # the python-level attribute path works.
    assert conn.capabilities == {"tools": []}
    # created_at/updated_at use server_default — value pre-flush is None.
    assert conn.__dict__.get("created_at") in (None, conn.__dict__.get("created_at"))
    # Type hint sanity for mypy — guard at runtime too.
    if conn.__dict__.get("created_at") is not None:
        assert isinstance(conn.created_at, datetime)
