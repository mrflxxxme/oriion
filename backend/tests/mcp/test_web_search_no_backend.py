"""Unit: WebSearchTool raises WebSearchError when no backend configured."""

from __future__ import annotations

import pytest
from src.mcp.exceptions import WebSearchError
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.mcp.tools.web_search import WebSearchTool


@pytest.mark.asyncio
async def test_no_backend_no_mock_raises(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)

    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter)
    with pytest.raises(WebSearchError, match="no_search_backend_configured"):
        await tool.search("anything", agent_id="agent-1")


@pytest.mark.asyncio
async def test_empty_env_strings_treated_as_unset(
    fake_redis: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty-string env-vars must NOT be treated as a configured backend."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "   ")
    monkeypatch.delenv("WEB_SEARCH_MOCK_MODE", raising=False)
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    tool = WebSearchTool(rate_limiter=limiter)
    with pytest.raises(WebSearchError, match="no_search_backend_configured"):
        await tool.search("anything", agent_id="agent-1")
