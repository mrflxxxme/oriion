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
        """Yandex Search XML API (yandex.ru/search/xml).

        Real Yandex Search returns XML; test mocks send a normalised JSON shape.
        We try ``.json()`` first (mocks) and fall back to the XML parser
        (AC-W1-18) for the live RU-sovereign path.
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
                    # XML path (AC-W1-18): parse the live Yandex Search XML.
                    return _parse_yandex_xml(response.text, max_results)
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


def _flatten_xml_text(el: Any) -> str:
    """Flatten an element's inline text (incl. ``<hlword>`` highlight markup)
    to whitespace-normalised plain text. Returns "" for a missing element."""
    if el is None:
        return ""
    return " ".join("".join(el.itertext()).split())


def _parse_yandex_xml(xml_text: str, max_results: int) -> list[WebSearchResult]:
    """Parse a live Yandex Search XML response → list[WebSearchResult] (AC-W1-18).

    Yandex Search XML (yandex.ru/search/xml) nests hits as
    ``response/results/grouping/group/doc`` with a ``<url>``, a ``<title>``
    carrying inline ``<hlword>`` highlight tags, and ``<passages>/<passage>``
    snippets (falling back to ``<headline>``). We flatten the highlight markup
    and prefer passage text.

    Degrades gracefully: a malformed body or a Yandex ``<error>`` element logs a
    warning and returns ``[]`` (matching the rest of the search path, which lets
    the Researcher fall back to LLM-only synthesis rather than failing the run).

    Hardened against XXE / entity-expansion (defence-in-depth even though the
    Yandex endpoint is trusted): the parser resolves no entities, loads no DTD
    and makes no network calls.
    """
    from lxml import etree

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=True,
    )
    try:
        # S320 suppressed: the parser above is hardened against the XML attacks
        # bandit warns about (no entity resolution, no DTD load, no network) — the
        # modern lxml mitigation, since defusedxml.lxml is itself deprecated.
        root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)  # noqa: S320
    except etree.XMLSyntaxError as exc:
        logger.warning("mcp.tools.web_search.yandex.xml_parse_error", error=str(exc))
        return []
    if root is None:
        return []

    error_el = root.find(".//error")
    if error_el is not None:
        logger.warning(
            "mcp.tools.web_search.yandex.api_error",
            code=error_el.get("code"),
            message=(error_el.text or "").strip(),
        )
        return []

    out: list[WebSearchResult] = []
    for doc in root.iterfind(".//doc"):
        url = (doc.findtext("url") or "").strip()
        if not url:
            continue
        title = _flatten_xml_text(doc.find("title"))
        snippet = _flatten_xml_text(doc.find(".//passages/passage")) or (
            doc.findtext("headline") or ""
        ).strip()
        out.append(WebSearchResult(title=title, url=url, snippet=snippet))
        if len(out) >= max_results:
            break
    return out
