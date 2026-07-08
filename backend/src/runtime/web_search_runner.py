"""Web-search builders for the Researcher leaf (extracted from runtime.dispatch).

Live web_search (Brave/Yandex) feeds the Researcher REAL market data instead of
LLM memory (founder decision 2026-06-07). Two paths, both formatting hits via
``_format_search_results`` so artifacts stay consistent:

* **Scripted pre-fetch** (``fetch_research_context``) — the YandexGPT/GigaChat
  failover path (ADR-035): a single deterministic web_search call before the
  Researcher LLM, snippets injected into its sub-prompt.
* **Native tool-call** (``build_native_web_search``) — the DeepSeek path
  (AC-W1-19): a Pydantic-AI ``web_search`` callable the model drives itself,
  throttled by the Redis ``ToolRateLimiter``.

``_default_web_search_tool`` constructs the ``WebSearchTool`` from Settings.

Extracted for the file-size canon split; the public symbols
(``fetch_research_context`` / ``build_native_web_search`` / ``WEB_SEARCH_MAX_RESULTS``)
are re-exported from ``runtime.dispatch`` for backward compatibility.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from src._shared.config import get_settings
from src.mcp.exceptions import MCPError, ToolRateLimitExceeded
from src.mcp.tools.read_url import ReadURLTool
from src.mcp.tools.web_search import WebSearchResult, WebSearchTool
from src.security.detectors.injection import scan_injection

if TYPE_CHECKING:
    from src.mcp.tools.rate_limit import ToolRateLimiter

# Live web_search (Brave) feeds the Researcher REAL market data instead of
# LLM memory (founder decision 2026-06-07). Wave-0 wires it as a scripted
# pre-fetch (the LLMGatewayModel tool-call path is AC14/AC-W1-16), so we call
# web_search deterministically before the Researcher LLM and inject the
# snippets into its sub-prompt. read_url + Yandex-XML backend are Wave-1 pins.
WEB_SEARCH_MAX_RESULTS = 6


def _sanitize_external(text: str) -> str:
    """B1-neutralize prompt-injection in external content before it reaches an
    agent (Phase 01.6, ADR-039). Gated by ``security_injection_scan_enabled``
    (default on); non-destructive and a no-op on benign content."""
    if not text or not get_settings().security_injection_scan_enabled:
        return text
    return scan_injection(text).neutralized_text


def _format_search_results(results: list[WebSearchResult]) -> str:
    """Format web_search hits as a citable markdown block (shared by the scripted
    pre-fetch and the native tool-call path so artifacts stay consistent).

    External snippets are B1-sanitized (ADR-039) before they reach the agent.
    """
    if not results:
        return ""
    lines = ["## Актуальные результаты веб-поиска (используй как источники, цитируй URL):"]
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. {r.title} — {r.url}\n   {r.snippet}")
    return _sanitize_external("\n".join(lines))


async def fetch_research_context(
    web_search_tool: WebSearchTool,
    query: str,
    *,
    max_results: int = WEB_SEARCH_MAX_RESULTS,
) -> str:
    """Run a live web_search and format the top hits as a markdown block.

    Scripted pre-fetch (the YandexGPT/GigaChat failover path — ADR-035): used when
    the active provider can't forward native tool-calls. Degrades gracefully: any
    web_search failure (no backend key configured, rate-limit, upstream/network
    error) returns "" so the Researcher falls back to LLM-only synthesis instead of
    failing the whole task run.
    """
    if not query.strip():
        return ""
    try:
        results = await web_search_tool.search(
            query, agent_id="researcher", max_results=max_results
        )
    except MCPError:  # WebSearchError + ToolRateLimitExceeded both subclass MCPError
        return ""
    return _format_search_results(results)


def build_native_web_search(
    web_search_tool: WebSearchTool,
    *,
    agent_id: str = "researcher",
    max_results: int = WEB_SEARCH_MAX_RESULTS,
) -> Callable[[str], Awaitable[str]]:
    """Build the native Pydantic-AI ``web_search`` tool callable (AC-W1-19).

    Bound to a rate-limited ``WebSearchTool`` + the Researcher ``agent_id`` so the
    Redis ``ToolRateLimiter`` throttles the agent's own search loop. Registered on
    the Researcher agent only on the DeepSeek path (ADR-035 gating in
    ``dispatch_task``). The returned coroutine's name + docstring + ``str`` param
    become the ``ToolDefinition`` forwarded to the provider.
    """

    async def web_search(query: str) -> str:
        """Search the web for up-to-date facts, competitors, prices and market data.

        Call this whenever the task needs current information you are unsure about.
        Pass a focused query in the user's language. Returns titled results with URLs
        to cite. Returns a short note if the rate limit is hit or no backend is set.
        """
        try:
            results = await web_search_tool.search(
                query, agent_id=agent_id, max_results=max_results
            )
        except ToolRateLimitExceeded:
            return "Лимит веб-поиска исчерпан — используй уже собранные результаты."
        except MCPError:
            # No backend configured / upstream error → let the model proceed
            # from its own knowledge rather than fail the run.
            return ""
        return _format_search_results(results) or "Результаты не найдены."

    return web_search


# read_url deep-read (AC-W1-18): the Researcher may fetch a promising source
# page beyond search snippets. Content is capped so the fed-back context (and
# thus the AC10 cost) stays bounded; the ReadURLTool itself is rate-limited to
# 10/min per agent_id (SSRF-guarded — see mcp/tools/read_url.py).
READ_URL_MAX_CHARS = 4000


def build_native_read_url(
    read_url_tool: ReadURLTool,
    *,
    agent_id: str = "researcher",
    max_chars: int = READ_URL_MAX_CHARS,
) -> Callable[[str], Awaitable[str]]:
    """Build the native Pydantic-AI ``read_url`` tool callable (AC-W1-18).

    Bound to a rate-limited ``ReadURLTool`` + the Researcher ``agent_id``.
    Registered on the Researcher only on the DeepSeek path (ADR-035 gating in
    ``dispatch_task``) so the model can deep-read a source page when search
    snippets aren't enough. Output is content-capped to ``max_chars`` to keep the
    fed-back context (and thus the AC10 cost) bounded. Degrades gracefully on
    rate-limit / SSRF-refusal / network errors so the run never fails on a
    single unreadable page.
    """

    async def read_url(url: str) -> str:
        """Fetch a web page by URL and return its main text content.

        Use after web_search to deep-read a promising source (competitor page,
        article, documentation) when the snippet isn't enough. Pass one http(s)
        URL. Returns a short note if the rate limit is hit or the page can't be
        read.
        """
        try:
            result = await read_url_tool.fetch(url, agent_id=agent_id)
        except ToolRateLimitExceeded:
            return "Лимит чтения страниц исчерпан — используй уже собранные данные."
        except MCPError:
            # SSRF refusal / network / extraction error → let the model proceed
            # from search snippets rather than fail the whole run.
            return ""
        text = result.text_content.strip()
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "…"
        # B1-sanitize the fetched page before it reaches the agent (ADR-039).
        text = _sanitize_external(text)
        if not text:
            return f"Страница {url} не содержит читаемого текста."
        header = f"## Содержимое страницы {result.url}"
        if result.title:
            header += f" — {result.title}"
        return f"{header}\n{text}"

    return read_url


def _default_web_search_tool(
    *,
    rate_limiter: ToolRateLimiter | None = None,
) -> WebSearchTool:
    """Construct a WebSearchTool from Settings (Brave key).

    ``rate_limiter`` is wired on the native tool-call path (AC-W1-19) so the
    Researcher's own search loop is throttled via Redis; the scripted pre-fetch
    path issues a single call per run and can pass ``None``. If no Brave/Yandex
    key is configured the tool raises at search-time and the Researcher leaf
    degrades to LLM-only (see fetch_research_context / build_native_web_search).
    """
    settings = get_settings()
    return WebSearchTool(
        rate_limiter=rate_limiter,
        brave_api_key=settings.brave_search_api_key.get_secret_value() or None,
        yandex_api_key=settings.yandex_search_api_key.get_secret_value() or None,
        # Folder (catalog) id required by the Yandex v2 searchAsync body; shared
        # with the LLM-gateway modelUri scheme (settings.yandex_catalog_id).
        yandex_folder_id=settings.yandex_catalog_id or None,
        # Settings is the source of truth — fixes AC-W1-19 bug where the tool read
        # os.environ directly so the .env WEB_SEARCH_MOCK_MODE flag was ignored
        # (live Brave 422 in the Track A run).
        mock_mode=settings.web_search_mock_mode,
    )


__all__ = [
    "READ_URL_MAX_CHARS",
    "WEB_SEARCH_MAX_RESULTS",
    "build_native_read_url",
    "build_native_web_search",
    "fetch_research_context",
]
