"""Domain exceptions for mcp.

Each exception carries an RFC 7807 `code` discriminator + HTTP `status_code`
so the eventual FastAPI exception handler can surface application/problem+json
responses without bespoke per-exception mapping. Mirrors iam.exceptions style.

Naming: per ADR-024 contract conformance, exception class names track error
codes rather than the Python ``Error``-suffix convention (ruff N818 is
allowed for ``**/exceptions.py`` in pyproject.toml).
"""

from __future__ import annotations


class MCPError(Exception):
    """Base domain exception for the mcp bounded context."""

    code: str = "mcp.error"
    status_code: int = 500
    title: str = "MCP error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


# ── Connection / framework errors ─────────────────────────────────────────


class MCPConnectionError(MCPError):
    """Failed to establish or speak to an MCP server.

    Wave 0 raised by the framework stub only when a caller misuses it
    (e.g. disconnecting a session that was never connected). Wave 1+ will
    surface real protocol-level failures (transport down, handshake reject).
    """

    code = "mcp.connection.error"
    status_code = 502
    title = "MCP connection error"


# ── Built-in tool errors ──────────────────────────────────────────────────


class ReadURLError(MCPError):
    """`read_url` built-in tool failed (network, parse, SSRF guard, etc.)."""

    code = "mcp.tools.read_url.error"
    status_code = 502
    title = "read_url tool error"


class WebSearchError(MCPError):
    """`web_search` built-in tool failed (no backend, upstream API error)."""

    code = "mcp.tools.web_search.error"
    status_code = 502
    title = "web_search tool error"


class ConnectorCredentialNotFound(MCPError):
    """Connector credential absent, revoked, or inactive for the workspace.

    Raised by ``connector_credential_service.get_credential_plaintext`` /
    ``revoke_credential`` when the (id, workspace) lookup yields no usable row —
    the belt-and-suspenders workspace filter on top of RLS. The message never
    echoes the secret (nothing to leak — only the id + workspace scope).
    """

    code = "mcp.connector_credential.not_found"
    status_code = 404
    title = "Connector credential not found"


class ToolRateLimitExceeded(MCPError):
    """Per-agent rate limit tripped for a built-in or MCP tool invocation.

    `retry_after` is the suggested cool-off window (seconds). Surface this
    via the `Retry-After` HTTP header in the eventual API exception handler.
    """

    code = "mcp.tools.rate_limit_exceeded"
    status_code = 429
    title = "Tool rate limit exceeded"

    def __init__(self, retry_after: int, detail: str | None = None) -> None:
        super().__init__(detail)
        self.retry_after = retry_after
