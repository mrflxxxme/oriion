"""Unit tests for ArtifactService — envelope CRUD, inline versions, soft-delete."""

from __future__ import annotations

from uuid import uuid4

import pytest
import structlog.testing
from src.artifacts.exceptions import ArtifactNotFound, ArtifactVersionNotFound
from src.artifacts.services.artifacts import ArtifactService, _canonical_json

from tests.artifacts._fakes import FakeArtifactRepo, FakeS3Repo, FakeUsageRepo, make_artifact


def _service(
    artifacts: FakeArtifactRepo, usage: FakeUsageRepo, s3_repo: FakeS3Repo
) -> ArtifactService:
    return ArtifactService(artifacts, usage, s3_repo)  # type: ignore[arg-type]


async def test_create_emits_event_and_lists() -> None:
    artifacts, usage, s3_repo = FakeArtifactRepo(), FakeUsageRepo(), FakeS3Repo()
    svc = _service(artifacts, usage, s3_repo)
    cell = uuid4()

    with structlog.testing.capture_logs() as logs:
        artifact = await svc.create(
            cell_id=cell, artifact_type="document", title="Brief", tags=["q3"]
        )
    assert artifact.current_version_num == 0
    ce_types = [entry.get("ce_type") for entry in logs if entry.get("cloudevent")]
    assert "oriion.artifacts.created.v1" in ce_types  # AC-01.5.8

    listed = await svc.list(cell_id=cell)
    assert [a.id for a in listed] == [artifact.id]
    assert await svc.list(cell_id=cell, artifact_type="asset") == []


async def test_inline_versions_number_sequentially() -> None:
    artifacts, usage, s3_repo = FakeArtifactRepo(), FakeUsageRepo(), FakeS3Repo()
    svc = _service(artifacts, usage, s3_repo)
    art = artifacts.add(make_artifact())

    v1 = await svc.create_inline_version(
        cell_id=art.cell_id, artifact_id=art.id, content={"text": "draft"}
    )
    v2 = await svc.create_inline_version(
        cell_id=art.cell_id, artifact_id=art.id, content={"text": "final"}
    )
    assert (v1.version_num, v2.version_num) == (1, 2)
    assert art.current_version_num == 2
    expected_bytes = len(_canonical_json({"text": "draft"})) + len(
        _canonical_json({"text": "final"})
    )
    assert usage.by_cell[art.cell_id] == expected_bytes  # AC-01.5.7

    got = await svc.get_version(cell_id=art.cell_id, artifact_id=art.id, version_num=1)
    assert got.content_inline == {"text": "draft"}
    with pytest.raises(ArtifactVersionNotFound):
        await svc.get_version(cell_id=art.cell_id, artifact_id=art.id, version_num=99)


async def test_list_versions_unknown_envelope_404() -> None:
    svc = _service(FakeArtifactRepo(), FakeUsageRepo(), FakeS3Repo())
    with pytest.raises(ArtifactNotFound):
        await svc.list_versions(cell_id=uuid4(), artifact_id=uuid4())


async def test_soft_delete_frees_usage_marks_s3_and_hides() -> None:
    artifacts, usage, s3_repo = FakeArtifactRepo(), FakeUsageRepo(), FakeS3Repo()
    svc = _service(artifacts, usage, s3_repo)
    art = artifacts.add(make_artifact())
    await svc.create_inline_version(
        cell_id=art.cell_id, artifact_id=art.id, content={"text": "data"}
    )
    stored = await s3_repo.insert_pending(
        cell_id=art.cell_id, artifact_id=art.id, bucket="b", s3_key="k"
    )
    await s3_repo.mark_stored(stored.id, byte_size=4, content_hash_sha256="x")
    assert usage.by_cell[art.cell_id] > 0

    with structlog.testing.capture_logs() as logs:
        await svc.soft_delete(cell_id=art.cell_id, artifact_id=art.id)

    assert usage.by_cell[art.cell_id] == 0  # logical bytes freed
    assert stored.status == "deleted"
    ce_types = [entry.get("ce_type") for entry in logs if entry.get("cloudevent")]
    assert "oriion.artifacts.deleted.v1" in ce_types
    with pytest.raises(ArtifactNotFound):  # hidden from get after soft-delete
        await svc.get(cell_id=art.cell_id, artifact_id=art.id)
    with pytest.raises(ArtifactNotFound):  # double delete → 404
        await svc.soft_delete(cell_id=art.cell_id, artifact_id=art.id)


async def test_usage_bytes_defaults_to_zero() -> None:
    svc = _service(FakeArtifactRepo(), FakeUsageRepo(), FakeS3Repo())
    assert await svc.usage_bytes(cell_id=uuid4()) == 0
