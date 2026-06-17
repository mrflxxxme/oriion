"""`web_search` built-in tool — Brave Search → Yandex Search fallback.

Phase 00.4 § Task 14 — 30 req/min per agent_id. Tries Brave Search API
first (``BRAVE_SEARCH_API_KEY``); if unset, falls back to Yandex Search
(``YANDEX_SEARCH_API_KEY``). If neither key is set and mock mode is off,
raises ``WebSearchError("no_search_backend_configured")``.

Mock mode
---------
Set ``WEB_SEARCH_MOCK_MODE=true`` to return canned results without any
HTTP traffic — required for CI runs that don't have search-API credentials.
Returns deterministic, predictable shape so consumers can assert on it.

Why two backends?
    * Brave Search is the global-default with a permissive API.
    * Yandex Search is required for RU-locale relevance + sovereignty
      (Phase 00.4 broader context — RU primary market). One of the two
      will always be available per environment; the gateway picks the
      first configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Final

import httpx
import structlog

from src.mcp.exceptions import ToolRateLimitExceeded, WebSearchError
from src.mcp.tools.rate_limit import ToolRateLimiter

logger = structlog.get_logger(__name__)

_TOOL_NAME: Final = "web_search"
_DEFAULT_LIMIT_PER_MIN: Final = 30
_DEFAULT_WINDOW_SECONDS: Final = 60
_DEFAULT_TIMEOUT_SECONDS: Final = 5.0

_BRAVE_API_URL: Final = "https://api.search.brave.com/res/v1/web/search"
_YANDEX_API_URL: Final = "https://yandex.ru/search/xml"


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    """Single search result row."""

    title: str
    url: str
    snippet: str


def _mock_mode_enabled_from_env() -> bool:
    """Legacy fallback: read WEB_SEARCH_MOCK_MODE from the environment directly.

    Used only when no explicit ``mock_mode`` is passed to ``WebSearchTool``.
    Settings.web_search_mock_mode is the source of truth on the dispatch path.
    """
    raw = os.environ.get("WEB_SEARCH_MOCK_MODE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _canned_mock_results(query: str, max_results: int) -> list[WebSearchResult]:
    """Deterministic canned results for CI + offline dev runs."""
    base = [
        WebSearchResult(
            title=f"Mock result {i + 1} for {query!r}",
            url=f"https://example.test/mock/{i + 1}",
            snippet=f"This is mock snippet {i + 1} matching {query!r}.",
        )
        for i in range(max_results)
    ]
    return base


class WebSearchTool:
    """Search the web. Rate-limited per agent_id; Brave → Yandex fallback."""

    def __init__(
        self,
        rate_limiter: ToolRateLimiter | None = None,
        *,
        limit_per_min: int = _DEFAULT_LIMIT_PER_MIN,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        brave_api_key: str | None = None,
        yandex_api_key: str | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        # rate_limiter is optional: the Wave-0 scripted-dispatch path
        # (runtime.dispatch) calls search() once per task run — far under the
        # 30/min cap — so it injects None and skips the Redis round-trip. The
        # MCP-tool surface + the Wave-1 LLM tool-call path always pass a real
        # ToolRateLimiter (defends against agent loops).
        self._rate_limiter = rate_limiter
        self._limit_per_min = limit_per_min
        self._timeout_seconds = timeout_seconds
        # mock_mode is Settings-driven when passed explicitly (the dispatch path
        # threads settings.web_search_mock_mode → fixes the AC-W1-19 bug where the
        # .env flag was ignored because the tool only read os.environ). When None
        # (MCP-tool surface / legacy callers) we fall back to the env-var read.
        self._mock_mode = mock_mode
        # Read env at construction so per-instance overrides are explicit.
        # Empty string treated as unset (env-var convention).
        self._brave_api_key = brave_api_key or (
            os.environ.get("BRAVE_SEARCH_API_KEY", "").strip() or None
        )
        self._yandex_api_key = yandex_api_key or (
            os.environ.get("YANDEX_SEARCH_API_KEY", "").strip() or None
        )

    async def search(
        self,
        query: str,
        agent_id: str = "system",
        max_results: int = 10,
    ) -> list[WebSearchResult]:
        """Run a web search. Returns up to `max_results` results."""
        if not query or not query.strip():
            raise WebSearchError("query must be non-empty")
        if max_results <= 0:
            raise WebSearchError("max_results must be > 0")

        # Rate limit gate (skipped when no limiter injected — see __init__) --
        if self._rate_limiter is not None:
            verdict = await self._rate_limiter.check_detailed(
                agent_id=agent_id,
                tool_name=_TOOL_NAME,
                limit=self._limit_per_min,
                window_seconds=_DEFAULT_WINDOW_SECONDS,
            )
            if not verdict.allowed:
                raise ToolRateLimitExceeded(
                    retry_after=verdict.retry_after,
                    detail=f"web_search limit {self._limit_per_min}/min exceeded",
                )

        # Mock-mode short-circuit -------------------------------------------
        mock_enabled = (
            self._mock_mode if self._mock_mode is not None else _mock_mode_enabled_from_env()
        )
        if mock_enabled:
            logger.info(
                "mcp.tools.web_search.mock_mode",
                query=query,
                agent_id=agent_id,
                max_results=max_results,
            )
            return _canned_mock_results(query, max_results)

        # Real backend dispatch ---------------------------------------------
        if self._brave_api_key:
            return await self._search_brave(query, max_results)
        if self._yandex_api_key:
            return await self._search_yandex(query, max_results)
        raise WebSearchError("no_search_backend_configured")

    async def _search_brave(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Brave Search Web API — returns up to `max_results` results.

        API docs: https://api.search.brave.com/app/documentation/web-search
        """
        # Type-narrow without bandit B101 — caller guarantees this by gating
        # on self._brave_api_key truthiness before dispatch.
        if self._brave_api_key is None:
            raise WebSearchError("brave_api_key not configured")
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._brave_api_key,
        }
        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_seconds)) as client:
                response = await client.get(_BRAVE_API_URL, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.RequestError as exc:
            raise WebSearchError(f"brave network error: {exc!s}") from exc
        except httpx.HTTPStatusError as exc:
            raise WebSearchError(f"brave http error: {exc.response.status_code}") from exc
        return _parse_brave(payload, max_results)

    async def _search_yandex(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Yandex Search XML API — JSON-mode subset.

        Real Yandex Search XML returns XML; Wave 0 we accept either JSON
        (test mocks) or treat XML as opaque text. Wave 1+ adds lxml parsing.
        """
        # Type-narrow without bandit B101 — caller guarantees this by gating
        # on self._yandex_api_key truthiness before dispatch.
        if self._yandex_api_key is None:
            raise WebSearchError("yandex_api_key not configured")
        params: dict[str, Any] = {
            "user": "oriion",
            "key": self._yandex_api_key,
            "query": query,
            "l10n": "ru",
            "groupby": f"attr=d.mode=deep.groups-on-page={max_results}",
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_seconds)) as client:
                response = await client.get(_YANDEX_API_URL, params=params)
                response.raise_for_status()
                # Tests stub a JSON body; real Yandex returns XML. Be permissive.
                try:
                    payload = response.json()
                except ValueError:
                    # XML path — Wave 1+ proper parsing. Wave 0 returns empty
                    # rather than guessing.
                    logger.warning(
                        "mcp.tools.web_search.yandex.xml_unparsed",
                        note="Wave 1+ adds XML parsing",
                    )
                    return []
        except httpx.RequestError as exc:
            raise WebSearchError(f"yandex network error: {exc!s}") from exc
        except httpx.HTTPStatusError as exc:
            raise WebSearchError(f"yandex http error: {exc.response.status_code}") from exc
        return _parse_yandex(payload, max_results)


def _parse_brave(payload: dict[str, Any], max_results: int) -> list[WebSearchResult]:
    """Parse Brave Search JSON response → list[WebSearchResult]."""
    web = payload.get("web") or {}
    results_raw = web.get("results") or []
    out: list[WebSearchResult] = []
    for item in results_raw[:max_results]:
        if not isinstance(item, dict):
            continue
        out.append(
            WebSearchResult(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                snippet=str(item.get("description") or ""),
            )
        )
    return out


def _parse_yandex(payload: dict[str, Any], max_results: int) -> list[WebSearchResult]:
    """Parse Yandex Search-style JSON response → list[WebSearchResult].

    Wave 0 expects a normalised shape from tests: {"results": [{...}]}.
    Real Yandex XML conversion lands Wave 1+.
    """
    results_raw = payload.get("results") or []
    out: list[WebSearchResult] = []
    for item in results_raw[:max_results]:
        if not isinstance(item, dict):
            continue
        out.append(
            WebSearchResult(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                snippet=str(item.get("snippet") or ""),
            )
        )
    return out
