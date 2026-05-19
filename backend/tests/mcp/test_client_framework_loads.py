"""Unit: AC8 — MCP client framework imports + instantiates.

Verifies Phase 00.4 AC8: `MCPClient` instantiates cleanly, `connect()`
returns an `MCPSession` with `tools=[]` (Wave 0 stub — no production MCP
servers; real protocol traffic lands Wave 1+).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from src.mcp.client import MCPClient, MCPSession, MCPTool
from src.mcp.exceptions import MCPConnectionError
from src.mcp.models import MCPConnection


def _make_connection(*, is_active: bool = True) -> MCPConnection:
    """Build an in-memory MCPConnection without touching a DB."""
    conn = MCPConnection(
        workspace_id=uuid4(),
        cell_id=None,
        name="brave-search",
        server_type="http",
        endpoint="https://example.test/mcp",
        capabilities={},
        is_active=is_active,
    )
    # Mimic server_default applied post-flush so client code doesn't NPE
    # when it stringifies `connection.id`.
    conn.id = uuid4()
    return conn


def test_mcp_client_instantiates() -> None:
    """AC8 — bare instantiation must not raise."""
    client = MCPClient()
    assert client is not None


@pytest.mark.asyncio
async def test_mcp_client_connect_returns_session_with_empty_tools() -> None:
    """AC8 — `connect()` returns session, `session.tools` is an empty list.

    Wave 0 stub behaviour: no protocol handshake, no tool discovery, but
    the seam is in place so Wave 1+ can swap in a real MCP SDK without
    touching callers.
    """
    client = MCPClient()
    conn = _make_connection()
    session = await client.connect(conn)
    assert isinstance(session, MCPSession)
    assert session.tools == []
    assert session.connected is True
    assert session.server_type == "http"
    assert session.connection_id == str(conn.id)


@pytest.mark.asyncio
async def test_mcp_client_disconnect_marks_session_closed() -> None:
    client = MCPClient()
    conn = _make_connection()
    session = await client.connect(conn)
    await client.disconnect(session)
    assert session.connected is False


@pytest.mark.asyncio
async def test_mcp_client_disconnect_idempotent() -> None:
    """Disconnecting twice must be a no-op (not raise)."""
    client = MCPClient()
    conn = _make_connection()
    session = await client.connect(conn)
    await client.disconnect(session)
    await client.disconnect(session)  # second call — no-op
    assert session.connected is False


@pytest.mark.asyncio
async def test_mcp_client_connect_rejects_inactive_connection() -> None:
    client = MCPClient()
    conn = _make_connection(is_active=False)
    with pytest.raises(MCPConnectionError):
        await client.connect(conn)


def test_mcp_tool_dataclass_defaults() -> None:
    """MCPTool exists with the Wave-1 expansion fields already declared."""
    tool = MCPTool(name="search")
    assert tool.name == "search"
    assert tool.description == ""
    assert tool.input_schema == {}
