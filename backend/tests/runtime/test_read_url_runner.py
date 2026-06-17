"""Unit: build_native_read_url — the Researcher's native deep-read tool (AC-W1-18)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.mcp.exceptions import ReadURLError, ToolRateLimitExceeded
from src.mcp.tools.read_url import ReadURLResult
from src.runtime.web_search_runner import build_native_read_url


class _FakeReadURLTool:
    """Stand-in for ReadURLTool.fetch — scripted result or exception."""

    def __init__(
        self, *, result: ReadURLResult | None = None, exc: Exception | None = None
    ) -> None:
        self._result = result
        self._exc = exc
        self.calls: list[tuple[str, str]] = []

    async def fetch(self, url: str, agent_id: str = "system") -> ReadURLResult:
        self.calls.append((url, agent_id))
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


@pytest.mark.asyncio
async def test_read_url_returns_capped_content_with_header() -> None:
    long_body = "слово " * 5000  # well over the cap
    tool = _FakeReadURLTool(
        result=ReadURLResult(
            url="https://example.test/page",
            title="Competitor pricing",
            text_content=long_body,
            fetched_at=datetime.now(UTC),
        )
    )
    read_url = build_native_read_url(tool, max_chars=200)  # type: ignore[arg-type]

    out = await read_url("https://example.test/page")

    assert out.startswith("## Содержимое страницы https://example.test/page — Competitor pricing")
    assert out.endswith("…")  # truncation marker
    assert len(out) < 400  # header + capped body, not the full 30k-char body
    assert tool.calls == [("https://example.test/page", "researcher")]


@pytest.mark.asyncio
async def test_read_url_rate_limit_returns_note() -> None:
    tool = _FakeReadURLTool(exc=ToolRateLimitExceeded(retry_after=30, detail="limit"))
    read_url = build_native_read_url(tool)  # type: ignore[arg-type]

    out = await read_url("https://example.test/page")

    assert "Лимит" in out  # graceful note, not an exception


@pytest.mark.asyncio
async def test_read_url_fetch_error_degrades_to_empty() -> None:
    # ReadURLError (SSRF refusal / network / extraction) subclasses MCPError →
    # the tool returns "" so the model proceeds from snippets instead of failing.
    tool = _FakeReadURLTool(exc=ReadURLError("refusing to fetch private address"))
    read_url = build_native_read_url(tool)  # type: ignore[arg-type]

    assert await read_url("http://169.254.169.254/") == ""
