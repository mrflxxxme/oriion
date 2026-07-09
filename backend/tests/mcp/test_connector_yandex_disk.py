"""Unit: yandex-disk connector — list/download over a MOCK transport + DLP/rate.

Covers AC-01.9b.1 (list parses / download returns content / draft returns text),
.2 (DLP blocks PII path arg before the external call), .7 (external call audited),
graceful no-cred degrade, and rate limiting — NO live network.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from src.mcp.exceptions import ToolRateLimitExceeded
from src.mcp.tools.connectors.base import HttpResponse
from src.mcp.tools.connectors.exceptions import (
    ConnectorDlpBlocked,
    ConnectorError,
    ConnectorNotConfigured,
)
from src.mcp.tools.connectors.yandex_disk import YandexDiskConnector
from src.mcp.tools.rate_limit import ToolRateLimiter

_INN_CTX = "ИНН 7830002293"  # valid ИНН-10 with labelling token (synthetic)

_LISTING = {
    "_embedded": {
        "items": [
            {"name": "brief.txt", "path": "disk:/brief.txt", "type": "file", "size": 42},
            {"name": "assets", "path": "disk:/assets", "type": "dir", "size": 0},
        ]
    }
}


class _FakeDisk:
    """Mock ``HttpTransport`` for the Disk REST API (list → download href → body)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        self.calls.append((method, url, headers))
        if url.endswith("/resources"):
            return HttpResponse(200, json.dumps(_LISTING).encode("utf-8"))
        if url.endswith("/resources/download"):
            return HttpResponse(200, json.dumps({"href": "https://downloader.test/abc"}).encode())
        return HttpResponse(200, b"file body content")


class _FakeAudit:
    def __init__(self) -> None:
        self.external: list[tuple[str, str, str]] = []

    async def record_external_call(
        self, *, connector_slug: str, tool_name: str, agent_id: str, outcome: str
    ) -> None:
        self.external.append((connector_slug, tool_name, outcome))

    async def record_dlp_block(
        self, *, connector_slug: str, tool_name: str, agent_id: str, categories: tuple[str, ...]
    ) -> None:  # pragma: no cover - not exercised here
        return None


@pytest.mark.asyncio
async def test_list_folder_parses_items_with_auth() -> None:
    tr = _FakeDisk()
    conn = YandexDiskConnector(credential="oauth-token", transport=tr)
    items = await conn.list_folder("/", agent_id="agent-1")
    assert [i.name for i in items] == ["brief.txt", "assets"]
    assert items[0].type == "file" and items[0].size == 42
    # OAuth token is carried in the Authorization header.
    assert tr.calls[0][2]["Authorization"] == "OAuth oauth-token"


@pytest.mark.asyncio
async def test_read_file_downloads_content() -> None:
    tr = _FakeDisk()
    conn = YandexDiskConnector(credential="oauth-token", transport=tr)
    content = await conn.read_file("disk:/brief.txt", agent_id="agent-1")
    assert content == "file body content"
    # Two-step: download-href request then the signed-href GET (no auth on GET).
    assert tr.calls[0][1].endswith("/resources/download")
    assert tr.calls[1][1] == "https://downloader.test/abc"


@pytest.mark.asyncio
async def test_draft_content_returns_text() -> None:
    conn = YandexDiskConnector(credential=None, transport=_FakeDisk())
    out = await conn.draft_content("  контент  ", agent_id="agent-1")
    assert out == "контент"


@pytest.mark.asyncio
async def test_missing_credential_degrades() -> None:
    conn = YandexDiskConnector(credential=None, transport=_FakeDisk())
    with pytest.raises(ConnectorNotConfigured):
        await conn.list_folder("/", agent_id="agent-1")


@pytest.mark.asyncio
async def test_dlp_blocks_path_with_pii_before_external_call() -> None:
    tr = _FakeDisk()
    conn = YandexDiskConnector(credential="oauth-token", transport=tr)
    with pytest.raises(ConnectorDlpBlocked) as ei:
        await conn.list_folder(f"/clients/{_INN_CTX}", agent_id="agent-1")
    assert "inn" in ei.value.categories
    assert tr.calls == []


@pytest.mark.asyncio
async def test_external_call_audited() -> None:
    audit = _FakeAudit()
    conn = YandexDiskConnector(credential="t", transport=_FakeDisk(), audit_sink=audit)
    await conn.list_folder("/", agent_id="agent-1")
    assert audit.external == [("yandex-disk", "yandex_disk_list", "success")]


@pytest.mark.asyncio
async def test_rate_limit_enforced(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    conn = YandexDiskConnector(
        credential="t", transport=_FakeDisk(), rate_limiter=limiter, limit_per_min=1
    )
    await conn.list_folder("/", agent_id="agent-1")
    with pytest.raises(ToolRateLimitExceeded):
        await conn.list_folder("/", agent_id="agent-1")


class _EmptyJson:
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any = None,
        params: Any = None,
        json_body: Any = None,
    ) -> HttpResponse:
        return HttpResponse(200, b"{}")


@pytest.mark.asyncio
async def test_list_degrades_to_empty_on_shapeless_payload() -> None:
    conn = YandexDiskConnector(credential="t", transport=_EmptyJson())
    assert await conn.list_folder("/", agent_id="agent-1") == []


@pytest.mark.asyncio
async def test_read_file_raises_without_download_href() -> None:
    conn = YandexDiskConnector(credential="t", transport=_EmptyJson())
    with pytest.raises(ConnectorError):
        await conn.read_file("disk:/x.txt", agent_id="agent-1")
