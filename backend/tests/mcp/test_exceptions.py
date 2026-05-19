"""Unit: mcp exception hierarchy + RFC 7807 metadata."""

from __future__ import annotations

from src.mcp.exceptions import (
    MCPConnectionError,
    MCPError,
    ReadURLError,
    ToolRateLimitExceeded,
    WebSearchError,
)


def test_base_error_carries_code_and_status() -> None:
    err = MCPError("custom detail")
    assert err.code == "mcp.error"
    assert err.status_code == 500
    assert str(err) == "custom detail"
    assert err.detail == "custom detail"


def test_base_error_falls_back_to_title() -> None:
    err = MCPError()
    assert str(err) == err.title


def test_connection_error_subclasses_base() -> None:
    err = MCPConnectionError("nope")
    assert isinstance(err, MCPError)
    assert err.status_code == 502
    assert err.code == "mcp.connection.error"


def test_read_url_error_metadata() -> None:
    err = ReadURLError("bad")
    assert err.code == "mcp.tools.read_url.error"
    assert err.status_code == 502


def test_web_search_error_metadata() -> None:
    err = WebSearchError("no backend")
    assert err.code == "mcp.tools.web_search.error"
    assert err.status_code == 502


def test_rate_limit_exceeded_carries_retry_after() -> None:
    err = ToolRateLimitExceeded(retry_after=42, detail="too fast")
    assert err.retry_after == 42
    assert err.status_code == 429
    assert err.code == "mcp.tools.rate_limit_exceeded"
    assert "too fast" in str(err)
