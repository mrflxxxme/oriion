"""`web_search` built-in tool — Brave Search → Yandex Search fallback.

Phase 00.4 § Task 14 — 30 req/min per agent_id. Brave Search API
(``BRAVE_SEARCH_API_KEY``) is the PRIMARY backend; if a Brave call *fails*
(network / HTTP / body-cap error) and a Yandex key is configured, we FALL
BACK to Yandex Search. If Brave is unset entirely, Yandex is used directly.
If neither backend is configured and mock mode is off, raises
``WebSearchError("no_search_backend_configured")``.

Mock mode
---------
Set ``WEB_SEARCH_MOCK_MODE=true`` to return canned results without any
HTTP traffic — required for CI runs that don't have search-API credentials.
Returns deterministic, predictable shape so consumers can assert on it.

Why two backends?
    * Brave Search is the global-default with a permissive API.
    * Yandex Search is the RU-sovereign fallback (Phase 00.4 broader context —
      RU primary market) and a resilience path when Brave is degraded.

Yandex backend — Cloud Search API v2 (async)
--------------------------------------------
The legacy synchronous XML interface (``yandex.ru/search/xml``) is DEAD: both
the ``user``+``key`` auth (error 4001) and the newer ``folderid``+``apikey``
sync-XML auth (error 4002 — "XML-search queries with the old version (v1) are
forbidden. Please use Yandex Cloud") are now rejected. The only live path is
the async Cloud Search API v2: ``POST /v2/web/searchAsync`` (``Authorization:
Api-Key`` header + JSON body carrying ``folderId``) returns an operation id;
we poll the Operation API until ``done`` and base64-decode the XML in
``response.rawData`` — which still matches the existing ``_parse_yandex_xml``
``<yandexsearch>`` shape. Docs: https://yandex.cloud/en/docs/search-api.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
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
# Cap the search-API response body (mirrors read_url): a compromised, spoofed
# (DNS/BGP) or buggy upstream could otherwise stream an unbounded body and
# OOM-kill the single Dramatiq worker before max_results can trim it.
_MAX_BODY_BYTES: Final = 5 * 1024 * 1024

_BRAVE_API_URL: Final = "https://api.search.brave.com/res/v1/web/search"
# Yandex Cloud Search API v2 (async): submit → poll → base64 XML. The legacy
# sync-XML endpoint is forbidden now (see module docstring).
_YANDEX_SEARCH_ASYNC_URL: Final = "https://searchapi.api.cloud.yandex.net/v2/web/searchAsync"
_YANDEX_OPERATION_URL: Final = "https://operation.api.cloud.yandex.net/operations/"
# Bounded poll loop kept inside the tool's timeout budget: if the operation
# hasn't completed we raise WebSearchError (the Brave→Yandex fallback / the
# Researcher's degrade-to-LLM path both handle it gracefully).
_YANDEX_POLL_MAX_ATTEMPTS: Final = 10
_YANDEX_POLL_INTERVAL_SECONDS: Final = 0.5


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
        yandex_folder_id: str | None = None,
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
        # Yandex Cloud folder (catalog) id — required by the v2 searchAsync body.
        # Threaded from settings.yandex_catalog_id on the dispatch path; env-var
        # fallback (YANDEX_CATALOG_ID) for the MCP-tool surface / legacy callers.
        self._yandex_folder_id = yandex_folder_id or (
            os.environ.get("YANDEX_CATALOG_ID", "").strip() or None
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

        # Real backend dispatch: Brave primary, Yandex fallback -------------
        if self._brave_api_key:
            try:
                return await self._search_brave(query, max_results)
            except WebSearchError as brave_exc:
                # Brave failed (network / HTTP / body-cap — all surfaced as
                # WebSearchError). Fall back to Yandex when a key is configured.
                if not self._yandex_api_key:
                    raise
                logger.warning(
                    "mcp.tools.web_search.brave_failed_fallback_yandex",
                    error=str(brave_exc),
                    query=query,
                )
                try:
                    return await self._search_yandex(query, max_results)
                except WebSearchError as yandex_exc:
                    # Both backends failed — surface the primary (Brave) error,
                    # which is the most informative for the caller.
                    logger.warning(
                        "mcp.tools.web_search.yandex_fallback_failed",
                        error=str(yandex_exc),
                        query=query,
                    )
                    raise brave_exc from yandex_exc
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
                body = await self._get_capped(
                    client, _BRAVE_API_URL, headers=headers, params=params
                )
        except httpx.RequestError as exc:
            raise WebSearchError(f"brave network error: {exc!s}") from exc
        except httpx.HTTPStatusError as exc:
            raise WebSearchError(f"brave http error: {exc.response.status_code}") from exc
        return _parse_brave(json.loads(body), max_results)

    async def _search_yandex(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Yandex Cloud Search API v2 (async) — submit → poll → base64 XML.

        The legacy sync-XML interface is forbidden now (module docstring): we
        ``POST /v2/web/searchAsync`` (``Authorization: Api-Key`` header, JSON
        body with ``folderId``) to get an operation id, poll the Operation API
        until ``done``, then base64-decode the XML in ``response.rawData`` and
        reuse ``_parse_yandex_xml`` (the ``<yandexsearch>`` shape is unchanged).
        """
        # Type-narrow without bandit B101 — caller guarantees the key by gating
        # on self._yandex_api_key truthiness before dispatch.
        if self._yandex_api_key is None:
            raise WebSearchError("yandex_api_key not configured")
        if not self._yandex_folder_id:
            raise WebSearchError("yandex_folder_id not configured (YANDEX_CATALOG_ID)")
        headers = {"Authorization": f"Api-Key {self._yandex_api_key}"}
        # Body mirrors the known-good v2 contract: deep grouping with one doc
        # per domain group so ``groupsOnPage`` caps the result count.
        request_body: dict[str, Any] = {
            "query": {
                "searchType": "SEARCH_TYPE_RU",
                "queryText": query,
                "familyMode": "FAMILY_MODE_NONE",
                "page": 0,
            },
            "sortSpec": {
                "sortMode": "SORT_MODE_BY_RELEVANCE",
                "sortOrder": "SORT_ORDER_DESC",
            },
            "groupSpec": {
                "groupMode": "GROUP_MODE_DEEP",
                "groupsOnPage": max_results,
                "docsInGroup": 1,
            },
            "maxPassages": 2,
            "l10N": "LOCALIZATION_RU",
            "folderId": self._yandex_folder_id,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_seconds)) as client:
                submit_body = await self._get_capped(
                    client,
                    _YANDEX_SEARCH_ASYNC_URL,
                    method="POST",
                    headers=headers,
                    json_body=request_body,
                )
                operation_id = _parse_operation_id(submit_body)
                xml_text = await self._poll_yandex_operation(client, operation_id, headers)
        except httpx.RequestError as exc:
            raise WebSearchError(f"yandex network error: {exc!s}") from exc
        except httpx.HTTPStatusError as exc:
            raise WebSearchError(f"yandex http error: {exc.response.status_code}") from exc
        return _parse_yandex_xml(xml_text, max_results)

    async def _poll_yandex_operation(
        self,
        client: httpx.AsyncClient,
        operation_id: str,
        headers: dict[str, str],
    ) -> str:
        """Poll the Operation API until ``done``; return the decoded XML text.

        Bounded to ``_YANDEX_POLL_MAX_ATTEMPTS`` short async sleeps. Raises
        ``WebSearchError`` on operation error, empty/undecodable ``rawData`` or
        a timeout — all of which the caller's fallback path degrades gracefully.
        """
        url = _YANDEX_OPERATION_URL + operation_id
        for _ in range(_YANDEX_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(_YANDEX_POLL_INTERVAL_SECONDS)
            poll_body = await self._get_capped(client, url, headers=headers)
            try:
                payload = json.loads(poll_body)
            except ValueError as exc:
                raise WebSearchError("yandex operation poll: non-JSON response") from exc
            if not payload.get("done"):
                continue
            error = payload.get("error")
            if error:
                raise WebSearchError(f"yandex operation error: {error}")
            raw_data = (payload.get("response") or {}).get("rawData")
            if not raw_data or not isinstance(raw_data, str):
                raise WebSearchError("yandex operation done but rawData empty")
            try:
                xml_bytes = base64.b64decode(raw_data, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise WebSearchError("yandex operation rawData is not valid base64") from exc
            return xml_bytes.decode("utf-8", errors="replace")
        raise WebSearchError("yandex operation poll timed out before done")

    async def _get_capped(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> bytes:
        """Request ``url`` and return the body, streaming with a hard size cap.

        Mirrors ``read_url``: the body is read chunk-by-chunk and aborted past
        ``_MAX_BODY_BYTES`` so an unbounded response (compromised/spoofed/buggy
        upstream) can't materialise into worker memory. ``raise_for_status``
        runs before any body read so an error status short-circuits. Supports a
        JSON POST body (the Yandex v2 searchAsync submit) as well as GET.
        """
        async with client.stream(
            method, url, headers=headers, params=params, json=json_body
        ) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > _MAX_BODY_BYTES:
                    raise WebSearchError(f"search response exceeded {_MAX_BODY_BYTES} bytes cap")
                chunks.append(chunk)
            return b"".join(chunks)


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


def _parse_operation_id(submit_body: bytes) -> str:
    """Extract the operation id from a Yandex v2 ``searchAsync`` submit response.

    The submit returns an Operation object ``{"id": "...", "done": false, ...}``.
    Raises ``WebSearchError`` if the body isn't JSON or carries no id.
    """
    try:
        payload = json.loads(submit_body)
    except ValueError as exc:
        raise WebSearchError("yandex searchAsync: non-JSON submit response") from exc
    operation_id = payload.get("id")
    if not isinstance(operation_id, str) or not operation_id:
        raise WebSearchError("yandex searchAsync: no operation id in response")
    return operation_id


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
    and makes no network calls. ``recover`` is OFF so a truncated/partial body
    raises (→ ``[]``) instead of being best-effort recovered into mangled hits
    (e.g. a half-streamed ``<title>`` surfaced as a real result).
    """
    from lxml import etree

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
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

    # Anchor the failure check to the documented top-level position
    # (``yandexsearch/response/error``) — a descendant ``.//error`` would nuke a
    # whole valid result set if any nested element happened to be named "error".
    error_el = root.find("./response/error")
    if error_el is None and root.tag == "response":
        error_el = root.find("./error")
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
        snippet = (
            _flatten_xml_text(doc.find(".//passages/passage"))
            or (doc.findtext("headline") or "").strip()
        )
        out.append(WebSearchResult(title=title, url=url, snippet=snippet))
        if len(out) >= max_results:
            break
    return out
