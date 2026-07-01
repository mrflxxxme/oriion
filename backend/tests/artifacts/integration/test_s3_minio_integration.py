"""Integration: full S3 flow against real MinIO (AC-01.5.4) + real PG.

presign (pending row = transactional key reservation, duplicate rejected) →
client HTTP POST upload via the presigned policy → complete (server-side
sha256/byte_size, pending→stored, version row) → signed GET within 1h TTL.

Endpoint/credentials come from MINIO_* env (defaults = infra/docker-compose
.dev.yml values). When MinIO is not reachable (e.g. the ci-backend GitHub job
has no MinIO service) the module SKIPS — the local Docker gate is the
authority for this AC per 01.5-PLAN risk note.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context
from src.artifacts.exceptions import S3KeyAlreadyReserved, UploadNotVerified
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository
from src.artifacts.repositories.s3_repository import S3ObjectRepository
from src.artifacts.services.artifacts import ArtifactService
from src.artifacts.services.s3 import Boto3ObjectStorage, S3AssetService

pytestmark = pytest.mark.integration

_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "oriion")
_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "oriion-dev-s3")
_BUCKET = os.environ.get("ARTIFACTS_S3_BUCKET", "oriion-artifacts-it")


def _minio_reachable() -> bool:
    try:
        response = httpx.get(f"{_ENDPOINT}/minio/health/ready", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


if not _minio_reachable():  # pragma: no cover — env-dependent guard
    pytest.skip(
        f"MinIO not reachable at {_ENDPOINT} — S3 flow is gated locally (Docker up)",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def object_storage() -> Boto3ObjectStorage:
    storage = Boto3ObjectStorage(
        endpoint_url=_ENDPOINT, access_key=_ACCESS_KEY, secret_key=_SECRET_KEY
    )
    # Ensure the bucket exists (idempotent).
    client: Any = storage._client_lazy()
    from botocore.exceptions import ClientError

    try:
        client.create_bucket(Bucket=_BUCKET)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
    return storage


async def _make_workspace_cell(session: AsyncSession) -> tuple[UUID, UUID]:
    ws_id, cell_id = uuid4(), uuid4()
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, 'WS')"
        ),
        {"id": str(ws_id), "slug": f"ws-{ws_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    return ws_id, cell_id


def _service(session: AsyncSession, storage: Boto3ObjectStorage) -> S3AssetService:
    return S3AssetService(
        S3ObjectRepository(session),
        ArtifactRepository(session),
        UsageRepository(session),
        storage,
        bucket=_BUCKET,
        env_prefix="it",
        max_upload_bytes=1024 * 1024,
    )


async def test_full_s3_flow_presign_upload_complete_signed_get(
    db_session: AsyncSession, object_storage: Boto3ObjectStorage
) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    art_svc = ArtifactService(
        ArtifactRepository(db_session), UsageRepository(db_session), S3ObjectRepository(db_session)
    )
    s3_svc = _service(db_session, object_storage)
    body = b"MinIO integration payload \x00\x01\x02 " + uuid4().bytes

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        artifact = await art_svc.create(cell_id=cell_id, artifact_type="asset", title="pic")

        # 1. presign — pending row is the transactional reservation.
        row, presigned = await s3_svc.presign_upload(
            cell_id=cell_id,
            artifact_id=artifact.id,
            filename="pic.bin",
            mime_type="application/octet-stream",
        )
        assert row.status == "pending"

        # A second presign for the SAME next version + filename → duplicate
        # key rejected at reservation time (AC-01.5.4 "дубль отклонён").
        with pytest.raises(S3KeyAlreadyReserved):
            await s3_svc.presign_upload(
                cell_id=cell_id, artifact_id=artifact.id, filename="pic.bin"
            )

        # complete BEFORE the client uploaded → verification fails, row stays pending.
        with pytest.raises(UploadNotVerified):
            await s3_svc.complete_upload(cell_id=cell_id, s3_object_id=row.id)

        # 2. client-side upload through the presigned POST policy.
        fields = presigned["fields"]
        assert isinstance(fields, dict)
        async with httpx.AsyncClient() as client:
            upload = await client.post(
                str(presigned["url"]),
                data=dict(fields),
                files={"file": ("pic.bin", body, "application/octet-stream")},
            )
        assert upload.status_code in (200, 201, 204), upload.text

        # 3. complete — server-side verification + version row.
        version, stored = await s3_svc.complete_upload(cell_id=cell_id, s3_object_id=row.id)
        assert stored.status == "stored"
        assert stored.byte_size == len(body)
        assert stored.content_hash_sha256 == hashlib.sha256(body).hexdigest()
        assert version.storage_kind == "s3" and version.version_num == 1

        # Usage accounted transactionally (AC-01.5.7 S3 leg).
        usage = (
            await db_session.execute(
                text("SELECT bytes_total FROM artifacts.cell_storage_usage WHERE cell_id = :c"),
                {"c": str(cell_id)},
            )
        ).scalar_one()
        assert usage == len(body)

        # 4. signed GET (1h TTL) — the bucket is never public.
        url = await s3_svc.download_url(cell_id=cell_id, s3_object_id=row.id)
        async with httpx.AsyncClient() as client:
            download = await client.get(url)
        assert download.status_code == 200
        assert download.content == body

        # Unsigned GET must NOT work (private bucket).
        async with httpx.AsyncClient() as client:
            unsigned = await client.get(f"{_ENDPOINT}/{_BUCKET}/{row.s3_key}")
        assert unsigned.status_code == 403
