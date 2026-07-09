"""yandex-disk connector — REST API READ (list / download) + DRAFT (Phase 01.9b).

Read = list a folder or download a file's content via the Yandex Disk REST API
(``https://cloud-api.yandex.net/v1/disk``), authenticated with an OAuth token.
Draft = prepare content for an artifact (no external call, no credential).

Transport is injectable (``HttpTransport``) so unit tests drive it with a mock;
the real ``HttpxTransport`` is used only when an OAuth token is configured
(deferred live-smoke, DV-11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from src.mcp.tools.connectors.base import BaseConnector, HttpResponse, HttpTransport, HttpxTransport
from src.mcp.tools.connectors.exceptions import ConnectorError

SLUG: Final = "yandex-disk"
TOOL_LIST: Final = "yandex_disk_list"
TOOL_READ_FILE: Final = "yandex_disk_read_file"
TOOL_DRAFT: Final = "yandex_disk_draft"

_API_BASE: Final = "https://cloud-api.yandex.net/v1/disk"
_DEFAULT_LIMIT: Final = 50


@dataclass(frozen=True, slots=True)
class DiskItem:
    """One Disk resource (file or dir) from a folder listing."""

    name: str
    path: str
    type: str
    size: int


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"OAuth {token}", "Accept": "application/json"}


def _parse_items(payload: Any, limit: int) -> list[DiskItem]:
    """Parse a Disk ``resources`` listing into items (degrades to [])."""
    if not isinstance(payload, dict):
        return []
    embedded = payload.get("_embedded")
    items = embedded.get("items") if isinstance(embedded, dict) else None
    if not isinstance(items, list):
        return []
    out: list[DiskItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        size = item.get("size")
        out.append(
            DiskItem(
                name=str(item.get("name") or ""),
                path=str(item.get("path") or ""),
                type=str(item.get("type") or ""),
                size=int(size) if isinstance(size, int) else 0,
            )
        )
        if len(out) >= limit:
            break
    return out


def _parse_download_href(payload: Any) -> str:
    """Extract the signed download href from a ``resources/download`` response."""
    href = payload.get("href") if isinstance(payload, dict) else None
    if not isinstance(href, str) or not href:
        raise ConnectorError("yandex-disk download: no href in response")
    return href


class YandexDiskConnector(BaseConnector):
    """Yandex Disk connector — list a folder, download a file, draft content."""

    def __init__(
        self,
        *,
        credential: str | None,
        transport: HttpTransport | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(connector_slug=SLUG, credential=credential, **base_kwargs)
        self._transport = transport or HttpxTransport()

    async def list_folder(
        self, path: str = "/", *, agent_id: str = "system", limit: int = _DEFAULT_LIMIT
    ) -> list[DiskItem]:
        """READ: list the resources under ``path``."""
        await self._rate_limit(agent_id, TOOL_LIST)
        await self._screen(TOOL_LIST, [path])
        token = self._require_credential()
        resp: HttpResponse = await self._transport.request(
            "GET",
            f"{_API_BASE}/resources",
            headers=_auth_headers(token),
            params={"path": path or "/", "limit": limit},
        )
        try:
            items = _parse_items(resp.json(), limit)
        except ValueError as exc:
            raise ConnectorError("yandex-disk list: non-JSON response") from exc
        await self._audit_external(TOOL_LIST, agent_id)
        return items

    async def read_file(self, path: str, *, agent_id: str = "system") -> str:
        """READ: download a file's content (get signed href → fetch body)."""
        await self._rate_limit(agent_id, TOOL_READ_FILE)
        await self._screen(TOOL_READ_FILE, [path])
        token = self._require_credential()
        meta: HttpResponse = await self._transport.request(
            "GET",
            f"{_API_BASE}/resources/download",
            headers=_auth_headers(token),
            params={"path": path},
        )
        try:
            href = _parse_download_href(meta.json())
        except ValueError as exc:
            raise ConnectorError("yandex-disk download: non-JSON response") from exc
        # The href is a short-lived signed URL — no auth header needed on the GET.
        content: HttpResponse = await self._transport.request("GET", href)
        await self._audit_external(TOOL_READ_FILE, agent_id)
        return content.text()

    async def draft_content(self, text: str, *, agent_id: str = "system") -> str:
        """DRAFT: prepare content for an artifact (no external call)."""
        await self._rate_limit(agent_id, TOOL_DRAFT)
        await self._screen(TOOL_DRAFT, [text])
        return text.strip()


__all__ = [
    "SLUG",
    "TOOL_DRAFT",
    "TOOL_LIST",
    "TOOL_READ_FILE",
    "DiskItem",
    "YandexDiskConnector",
]
