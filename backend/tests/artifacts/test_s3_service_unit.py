"""Unit tests for S3AssetService — fake port + fake repos, no network.

Validates: transactional key reservation (duplicate presign → 409), filename
sanitization (path traversal → 422), server-side verification at complete
(sha256/byte_size never trusted from the client), lifecycle transitions,
signed GET only for stored objects, and the stale-pending janitor.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import structlog.testing
from src.artifacts.exceptions import (
    ArtifactNotFound,
    InvalidFilename,
    S3KeyAlreadyReserved,
    S3ObjectNotFound,
    UploadNotVerified,
)
from src.artifacts.services.s3 import S3AssetService, sanitize_filename

from tests.artifacts._fakes import (
    FakeArtifactRepo,
    FakeObjectStorage,
    FakeS3Repo,
    FakeUsageRepo,
    make_artifact,
    sha256_hex,
)

_BUCKET = "test-bucket"


def _service(
    s3_repo: FakeS3Repo,
    artifacts: FakeArtifactRepo,
    usage: FakeUsageRepo,
    storage: FakeObjectStorage,
) -> S3AssetService:
    return S3AssetService(
        s3_repo,  # type: ignore[arg-type]
        artifacts,  # type: ignore[arg-type]
        usage,  # type: ignore[arg-type]
        storage,
        bucket=_BUCKET,
        env_prefix="test",
        max_upload_bytes=1024,
    )


def test_sanitize_filename_blocks_traversal_and_separators() -> None:
    for bad in ("../../etc/passwd", "a/b.png", "a\\b.png", "", ".hidden", "фото.png", "a" * 300):
        with pytest.raises(InvalidFilename):
            sanitize_filename(bad)
    assert sanitize_filename("report_v2.final-1.pdf") == "report_v2.final-1.pdf"


async def test_presign_reserves_key_and_returns_post_policy() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))

    row, presigned = await svc.presign_upload(
        cell_id=art.cell_id, artifact_id=art.id, filename="pic.png", mime_type="image/png"
    )
    assert row.status == "pending"
    assert row.s3_key == f"test/{art.cell_id}/{art.id}/1/pic.png"  # ADR-012 key shape
    assert "url" in presigned and "fields" in presigned


async def test_duplicate_presign_rejected_409() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))

    await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")
    with pytest.raises(S3KeyAlreadyReserved):
        await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")


async def test_presign_unknown_artifact_404() -> None:
    svc = _service(FakeS3Repo(), FakeArtifactRepo(), FakeUsageRepo(), FakeObjectStorage())
    with pytest.raises(ArtifactNotFound):
        await svc.presign_upload(cell_id=uuid4(), artifact_id=uuid4(), filename="pic.png")


async def test_complete_verifies_server_side_and_creates_version() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))
    row, _ = await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")

    body = b"actual-bytes-on-the-bucket"
    storage.put(_BUCKET, row.s3_key, body)  # simulate the client upload

    with structlog.testing.capture_logs() as logs:
        version, stored = await svc.complete_upload(cell_id=art.cell_id, s3_object_id=row.id)

    assert stored.status == "stored"
    assert stored.byte_size == len(body)  # computed server-side
    assert stored.content_hash_sha256 == sha256_hex(body)
    assert version.storage_kind == "s3"
    assert version.s3_object_id == row.id
    assert version.version_num == 1
    assert art.current_version_num == 1
    assert usage.by_cell[art.cell_id] == len(body)  # AC-01.5.7
    ce_types = [entry.get("ce_type") for entry in logs if entry.get("cloudevent")]
    assert "oriion.artifacts.s3.asset_uploaded.v1" in ce_types  # AC-01.5.8


async def test_complete_without_uploaded_object_409() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))
    row, _ = await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")

    with pytest.raises(UploadNotVerified):
        await svc.complete_upload(cell_id=art.cell_id, s3_object_id=row.id)
    assert row.status == "pending"  # untouched


async def test_double_complete_409() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))
    row, _ = await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")
    storage.put(_BUCKET, row.s3_key, b"body")
    await svc.complete_upload(cell_id=art.cell_id, s3_object_id=row.id)

    with pytest.raises(UploadNotVerified):
        await svc.complete_upload(cell_id=art.cell_id, s3_object_id=row.id)
    assert len(artifacts.versions) == 1  # no duplicate version row


async def test_download_url_only_for_stored() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))
    row, _ = await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")

    with pytest.raises(S3ObjectNotFound):  # pending is not downloadable
        await svc.download_url(cell_id=art.cell_id, s3_object_id=row.id)

    storage.put(_BUCKET, row.s3_key, b"body")
    await svc.complete_upload(cell_id=art.cell_id, s3_object_id=row.id)
    url = await svc.download_url(cell_id=art.cell_id, s3_object_id=row.id)
    assert row.s3_key in url and "signed=1" in url


async def test_purge_stale_pending_janitor() -> None:
    s3_repo, artifacts, usage, storage = (
        FakeS3Repo(),
        FakeArtifactRepo(),
        FakeUsageRepo(),
        FakeObjectStorage(),
    )
    svc = _service(s3_repo, artifacts, usage, storage)
    art = artifacts.add(make_artifact(artifact_type="asset"))
    row, _ = await svc.presign_upload(cell_id=art.cell_id, artifact_id=art.id, filename="pic.png")

    assert await svc.purge_stale_pending(cell_id=art.cell_id) == 0  # fresh — kept
    row.created_at = datetime.now(UTC) - timedelta(hours=1)  # age the reservation
    assert await svc.purge_stale_pending(cell_id=art.cell_id) == 1
    assert await s3_repo.get(row.id, cell_id=art.cell_id) is None
