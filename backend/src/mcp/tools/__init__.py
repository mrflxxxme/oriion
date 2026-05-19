"""Built-in tools — first-party utilities shared with the MCP tool surface.

Wave 0 ships two tools (Phase 00.4 § Task 14):
    * `read_url`   — fetch + extract main content (httpx + readability-lxml).
    * `web_search` — Brave / Yandex Search with mock-mode for CI.

These are NOT MCP servers themselves — they're first-party tool
implementations the LLM gateway / agent runtime can call directly. They
share the rate-limit (`ToolRateLimiter`) + exception surface (`MCPError`
descendants) that production MCP tool invocation will eventually use, so
the call-site abstraction is uniform.
"""

from __future__ import annotations
