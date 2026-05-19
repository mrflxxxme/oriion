"""MCP client wrapper — Wave 0 STUB.

Wave 0 scope (Phase 00.4 AC8): the framework imports + instantiates cleanly,
and exposes a Pydantic-AI / official ``mcp`` SDK-compatible surface
(``connect`` returns a session with a ``tools`` list). **No real MCP protocol
traffic happens Wave 0** — production MCP servers are deferred to Wave 1+
where the real ``mcp.ClientSession`` (or Pydantic-AI ``MCPServer`` adapter)
will replace this stub.

This file is intentionally small. Its job in Wave 0:
    1. Anchor the import path ``src.mcp.client`` that downstream code (LLM
       gateway tool routing, agent runtime) will start depending on.
    2. Give tests a stable seam (``test_mcp_client_framework_loads``).
    3. Document the Wave-1 expansion contract so the swap is mechanical.

When Wave 1 ships real MCP, only the bodies of ``connect`` / ``disconnect``
+ the session model change. The public method signatures + class names
stay; callers do not need to update.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.mcp.exceptions import MCPConnectionError
from src.mcp.models import MCPConnection

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MCPTool:
    """In-memory representation of an MCP-advertised tool.

    Wave 0: never populated (no real handshake). Wave 1+ will fill name +
    input_schema + description from the MCP server's `tools/list` response.
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MCPSession:
    """Active MCP session handle.

    Wave 0: pure in-memory record — no transport, no protocol state.
    The `connected` flag is the seam tests use to assert framework wiring
    without touching real I/O.
    """

    connection_id: str
    server_type: str
    endpoint: str
    tools: list[MCPTool] = field(default_factory=list)
    connected: bool = True


class MCPClient:
    """Async MCP client wrapper.

    Wave 0 behavior:
        * ``connect`` returns a fresh ``MCPSession`` with ``tools=[]``.
        * ``disconnect`` flips ``connected`` to False and logs.

    Wave 1+ planned expansion:
        * Spawn the underlying ``mcp.ClientSession`` (stdio: subprocess +
          pipes; http: streaming endpoint).
        * Perform the MCP handshake + ``tools/list`` discovery.
        * Cache server capabilities on the session.

    The class is stateless — multiple `connect()` calls can run in
    parallel without contention; sessions are owned by the caller.
    """

    def __init__(self) -> None:
        # No I/O setup Wave 0. Wave 1+ may inject a tool-registry / cache here.
        logger.debug("mcp.client.instantiated")

    async def connect(self, connection: MCPConnection) -> MCPSession:
        """Open a session against the given registered connection.

        Wave 0: returns an empty session immediately (no transport). The
        caller (or test) can inspect ``session.tools`` to confirm the
        framework-loads contract from AC8.
        """
        if not connection.is_active:
            raise MCPConnectionError(f"connection {connection.name!r} is not active")

        session = MCPSession(
            connection_id=str(connection.id),
            server_type=connection.server_type,
            endpoint=connection.endpoint,
            tools=[],
            connected=True,
        )
        logger.info(
            "mcp.client.connect",
            connection_id=session.connection_id,
            server_type=session.server_type,
            wave="0",
            note="stub-no-protocol-traffic",
        )
        return session

    async def disconnect(self, session: MCPSession) -> None:
        """Tear down an active session.

        Wave 0: marks the session disconnected + logs. Idempotent — calling
        on an already-closed session is a no-op (warn-level log).
        """
        if not session.connected:
            logger.warning(
                "mcp.client.disconnect.already_closed",
                connection_id=session.connection_id,
            )
            return
        session.connected = False
        logger.info(
            "mcp.client.disconnect",
            connection_id=session.connection_id,
        )
