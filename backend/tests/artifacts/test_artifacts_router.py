"""Router-wiring tests for the artifacts API (no DB; services + auth faked).

Validates request/response shapes, status codes, RFC-7807 mapping of domain
errors (404 artifacts.not_found, 422 artifacts.malformed_url, 409 reserved
key), base64 validation on the Yjs update path and the /usage + /resolve
literal-route ordering. Real RLS/pycrdt/MinIO live in the integration suite.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest_asyncio
from httpx import ASGITransport
from src.artifacts.exceptions import ArtifactNotFound, S3KeyAlreadyReserved
from src.artifacts.services.resolver import ResolvedArtifact, parse_artifact_url

_CELL = uuid4()
_USER = uuid4()
_NOW = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)


def _artifact_row(**over: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "id": uuid4(),
        "cell_id": _CELL,
        "artifact_type": "document",
        "title": "Brief",
        "tags": ["q3"],
        "owner_user_id": _USER,
        "created_by_agent_id": None,
        "current_version_num": 0,
        "deleted_at": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(over)
    return SimpleNamespace(**base)


def _version_row(artifact_id: UUID, **over: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "id": uuid4(),
        "artifact_id": artifact_id,
        "cell_id": _CELL,
        "version_num": 1,
        "storage_kind": "inline",
        "content_inline": {"text": "hi"},
        "s3_object_id": None,
        "yjs_snapshot_id": None,
        "byte_size": 2,
        "content_hash_sha256": "ab" * 32,
        "created_at": _NOW,
    }
    base.update(over)
    return SimpleNamespace(**base)


class _FakeArtifactSvc:
    def __init__(self) -> None:
        self.rows: list[SimpleNamespace] = []
        self.raise_not_found = False
        self.deleted: list[UUID] = []
        self.usage = 1234

    async def create(self, **kw: Any) -> SimpleNamespace:
        row = _artifact_row(
            artifact_type=kw["artifact_type"],
            title=kw["title"],
            tags=list(kw["tags"]),
            owner_user_id=kw["owner_user_id"],
            created_by_agent_id=kw["created_by_agent_id"],
        )
        self.rows.append(row)
        return row

    async def get(self, *, cell_id: UUID, artifact_id: UUID) -> SimpleNamespace:
        for row in self.rows:
            if row.id == artifact_id:
                return row
        raise ArtifactNotFound(str(artifact_id))

    async def list(self, **kw: Any) -> list[SimpleNamespace]:
        return self.rows

    async def soft_delete(self, *, cell_id: UUID, artifact_id: UUID) -> None:
        if self.raise_not_found:
            raise ArtifactNotFound(str(artifact_id))
        self.deleted.append(artifact_id)

    async def create_inline_version(self, **kw: Any) -> SimpleNamespace:
        return _version_row(kw["artifact_id"], content_inline=kw["content"])

    async def get_version(self, **kw: Any) -> SimpleNamespace:
        return _version_row(kw["artifact_id"], version_num=kw["version_num"])

    async def list_versions(self, **kw: Any) -> list[SimpleNamespace]:
        return [_version_row(kw["artifact_id"])]

    async def usage_bytes(self, *, cell_id: UUID) -> int:
        return self.usage


class _FakeYjsSvc:
    def __init__(self) -> None:
        self.applied: list[bytes] = []
        self._doc = SimpleNamespace(
            id=uuid4(),
            artifact_id=uuid4(),
            state=b"\x00\x00",
            state_vector=b"\x00",
            update_count=0,
            last_compacted_at=None,
        )

    async def create_document(self, *, cell_id: UUID, artifact_id: UUID) -> SimpleNamespace:
        self._doc.artifact_id = artifact_id
        return self._doc

    async def get_document(self, *, cell_id: UUID, artifact_id: UUID) -> SimpleNamespace:
        return self._doc

    async def apply_update(
        self, *, cell_id: UUID, artifact_id: UUID, update_data: bytes
    ) -> SimpleNamespace:
        self.applied.append(update_data)
        self._doc.update_count += 1
        return self._doc

    async def commit_version(self, **kw: Any) -> tuple[SimpleNamespace, SimpleNamespace]:
        version = _version_row(
            kw["artifact_id"],
            storage_kind="yjs_snapshot",
            content_inline=None,
            yjs_snapshot_id=uuid4(),
        )
        snapshot = SimpleNamespace(id=version.yjs_snapshot_id, state=b"\x00\x00")
        return version, snapshot


class _FakeS3Svc:
    def __init__(self) -> None:
        self.raise_reserved = False

    async def presign_upload(self, **kw: Any) -> tuple[SimpleNamespace, dict[str, Any]]:
        if self.raise_reserved:
            raise S3KeyAlreadyReserved("dup-key")
        row = SimpleNamespace(
            id=uuid4(),
            artifact_id=kw["artifact_id"],
            bucket="b",
            s3_key=f"test/{kw['artifact_id']}/1/{kw['filename']}",
            mime_type=kw["mime_type"],
            byte_size=None,
            content_hash_sha256=None,
            status="pending",
        )
        return row, {"url": "https://s3.local/b", "fields": {"key": row.s3_key}}

    async def complete_upload(self, **kw: Any) -> tuple[SimpleNamespace, SimpleNamespace]:
        artifact_id = uuid4()
        version = _version_row(
            artifact_id, storage_kind="s3", content_inline=None, s3_object_id=kw["s3_object_id"]
        )
        s3_object = SimpleNamespace(
            id=kw["s3_object_id"],
            artifact_id=artifact_id,
            bucket="b",
            s3_key="test/k",
            mime_type=None,
            byte_size=4,
            content_hash_sha256="h",
            status="stored",
        )
        return version, s3_object

    async def download_url(self, *, cell_id: UUID, s3_object_id: UUID) -> str:
        return "https://s3.local/b/k?signed=1"


class _FakeResolver:
    """Real strict parse + canned resolution — 422/404 semantics preserved."""

    async def resolve(self, url: str, *, current_cell_id: UUID) -> ResolvedArtifact:
        parsed = parse_artifact_url(url)  # raises MalformedArtifactUrl → 422
        if parsed.cell_id != current_cell_id:
            raise ArtifactNotFound(url)
        return ResolvedArtifact(
            artifact_id=parsed.artifact_id,
            cell_id=parsed.cell_id,
            artifact_type="document",
            title="Brief",
            version_num=parsed.version_num or 3,
            storage_kind="inline",
            byte_size=2,
            content_hash_sha256="h",
            content_inline={"text": "hi"},
        )


@pytest_asyncio.fixture
async def ctx() -> (
    AsyncIterator[tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc]]
):
    from src._shared.middleware.tenant_context import get_current_cell_id
    from src.artifacts.deps import (
        get_artifact_resolver,
        get_artifact_service,
        get_s3_asset_service,
        get_yjs_service,
    )
    from src.iam.middleware import get_current_user
    from src.main import app

    art_svc, yjs_svc, s3_svc = _FakeArtifactSvc(), _FakeYjsSvc(), _FakeS3Svc()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user=SimpleNamespace(id=_USER)
    )
    app.dependency_overrides[get_current_cell_id] = lambda: _CELL
    app.dependency_overrides[get_artifact_service] = lambda: art_svc
    app.dependency_overrides[get_yjs_service] = lambda: yjs_svc
    app.dependency_overrides[get_s3_asset_service] = lambda: s3_svc
    app.dependency_overrides[get_artifact_resolver] = lambda: _FakeResolver()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, art_svc, yjs_svc, s3_svc
    app.dependency_overrides.clear()


async def test_create_and_list_artifacts(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, art_svc, _, _ = ctx
    resp = await client.post(
        "/api/v1/artifacts",
        json={"artifact_type": "document", "title": "Brief", "tags": ["q3"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["artifact_type"] == "document"
    assert body["owner_user_id"] == str(_USER)
    assert body["current_version_num"] == 0

    listed = await client.get("/api/v1/artifacts")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_create_rejects_unknown_type_and_extras(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, _, _, _ = ctx
    bad_type = await client.post(
        "/api/v1/artifacts", json={"artifact_type": "spreadsheet", "title": "x"}
    )
    assert bad_type.status_code == 422
    extra = await client.post(
        "/api/v1/artifacts",
        json={"artifact_type": "document", "title": "x", "nope": 1},
    )
    assert extra.status_code == 422


async def test_get_unknown_artifact_is_rfc7807_404(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, _, _, _ = ctx
    resp = await client.get(f"/api/v1/artifacts/{uuid4()}")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["code"] == "artifacts.not_found"


async def test_inline_version_roundtrip(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, _, _, _ = ctx
    artifact_id = uuid4()
    resp = await client.post(
        f"/api/v1/artifacts/{artifact_id}/versions",
        json={"content": {"text": "hi"}},
    )
    assert resp.status_code == 201
    assert resp.json()["storage_kind"] == "inline"

    versions = await client.get(f"/api/v1/artifacts/{artifact_id}/versions")
    assert versions.status_code == 200 and len(versions.json()) == 1
    one = await client.get(f"/api/v1/artifacts/{artifact_id}/versions/1")
    assert one.status_code == 200 and one.json()["version_num"] == 1


async def test_delete_artifact_204(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, art_svc, _, _ = ctx
    target = uuid4()
    resp = await client.delete(f"/api/v1/artifacts/{target}")
    assert resp.status_code == 204
    assert art_svc.deleted == [target]


async def test_yjs_flow_shapes(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, _, yjs_svc, _ = ctx
    artifact_id = uuid4()

    created = await client.post(f"/api/v1/artifacts/{artifact_id}/yjs")
    assert created.status_code == 201
    assert created.json()["state_base64"] == base64.b64encode(b"\x00\x00").decode()

    update = base64.b64encode(b"update-bytes").decode()
    applied = await client.post(
        f"/api/v1/artifacts/{artifact_id}/yjs/updates", json={"update_base64": update}
    )
    assert applied.status_code == 200
    assert yjs_svc.applied == [b"update-bytes"]  # decoded server-side

    bad = await client.post(
        f"/api/v1/artifacts/{artifact_id}/yjs/updates",
        json={"update_base64": "!!!not-base64!!!"},
    )
    assert bad.status_code == 422  # pydantic validator rejects

    committed = await client.post(f"/api/v1/artifacts/{artifact_id}/yjs/commit")
    assert committed.status_code == 201
    body = committed.json()
    assert body["version"]["storage_kind"] == "yjs_snapshot"
    assert body["artifact_url"].startswith(f"artifact://{_CELL}/{artifact_id}/v")


async def test_upload_presign_complete_and_download(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, _, _, s3_svc = ctx
    artifact_id = uuid4()

    presigned = await client.post(
        f"/api/v1/artifacts/{artifact_id}/uploads",
        json={"filename": "pic.png", "mime_type": "image/png"},
    )
    assert presigned.status_code == 201
    pbody = presigned.json()
    assert pbody["upload_url"] and pbody["upload_fields"]["key"] == pbody["s3_key"]
    assert pbody["expires_in_seconds"] == 300  # ADR-012: 5-min POST TTL

    s3_object_id = pbody["s3_object_id"]
    completed = await client.post(f"/api/v1/artifacts/uploads/{s3_object_id}/complete")
    assert completed.status_code == 201
    cbody = completed.json()
    assert cbody["version"]["storage_kind"] == "s3"
    assert cbody["s3_object"]["status"] == "stored"

    download = await client.get(f"/api/v1/artifacts/uploads/{s3_object_id}/download-url")
    assert download.status_code == 200
    dbody = download.json()
    assert "signed=1" in dbody["url"]
    assert dbody["expires_in_seconds"] == 3600  # ADR-012: 1-hour GET TTL

    s3_svc.raise_reserved = True
    dup = await client.post(
        f"/api/v1/artifacts/{artifact_id}/uploads", json={"filename": "pic.png"}
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "artifacts.s3_key_reserved"


async def test_usage_endpoint(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, art_svc, _, _ = ctx
    resp = await client.get("/api/v1/artifacts/usage")
    assert resp.status_code == 200
    assert resp.json() == {"cell_id": str(_CELL), "bytes_total": art_svc.usage}


async def test_resolve_endpoint_semantics(
    ctx: tuple[httpx.AsyncClient, _FakeArtifactSvc, _FakeYjsSvc, _FakeS3Svc],
) -> None:
    client, _, _, _ = ctx
    artifact_id = uuid4()

    ok = await client.get(
        "/api/v1/artifacts/resolve", params={"url": f"artifact://{_CELL}/{artifact_id}/v3"}
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["version_num"] == 3 and body["content_inline"] == {"text": "hi"}
    assert body["artifact_url"] == f"artifact://{_CELL}/{artifact_id}/v3"

    malformed = await client.get("/api/v1/artifacts/resolve", params={"url": "artifact://oops"})
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "artifacts.malformed_url"

    foreign = await client.get(
        "/api/v1/artifacts/resolve", params={"url": f"artifact://{uuid4()}/{artifact_id}"}
    )
    assert foreign.status_code == 404
    assert foreign.json()["code"] == "artifacts.not_found"
