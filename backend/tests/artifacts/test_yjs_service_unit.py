"""Unit tests for YjsService — REAL pycrdt merge logic over fake repos.

Validates: create-once semantics, CRDT merge of two independent replicas
(read-your-writes on the returned head), invalid-update rejection, explicit
commit → snapshot + immutable version + usage bytes, and compaction pruning
the update log but never snapshots (AC-01.5.3).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pycrdt import Doc, Text
from src.artifacts.exceptions import (
    ArtifactNotFound,
    ArtifactTypeMismatch,
    InvalidYjsUpdate,
    YjsDocumentAlreadyExists,
    YjsDocumentNotFound,
)
from src.artifacts.services.yjs import YjsService

from tests.artifacts._fakes import FakeArtifactRepo, FakeUsageRepo, FakeYjsRepo, make_artifact


def _service(
    yjs: FakeYjsRepo,
    artifacts: FakeArtifactRepo,
    usage: FakeUsageRepo,
    **over: int,
) -> YjsService:
    return YjsService(yjs, artifacts, usage, **over)  # type: ignore[arg-type]


def _client_update(text: str) -> bytes:
    doc = Doc()
    body = doc.get("body", type=Text)
    body += text
    return doc.get_update()


def _head_text(state: bytes) -> str:
    doc = Doc()
    doc.apply_update(state)
    return str(doc.get("body", type=Text))


async def test_create_document_requires_document_or_code_artifact() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    asset = artifacts.add(make_artifact(artifact_type="asset"))

    with pytest.raises(ArtifactTypeMismatch):
        await svc.create_document(cell_id=asset.cell_id, artifact_id=asset.id)
    with pytest.raises(ArtifactNotFound):
        await svc.create_document(cell_id=asset.cell_id, artifact_id=uuid4())


async def test_create_document_is_idempotent_guarded() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    art = artifacts.add(make_artifact())

    row = await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)
    assert row.update_count == 0
    with pytest.raises(YjsDocumentAlreadyExists):
        await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)


async def test_apply_update_merges_two_replicas_read_your_writes() -> None:
    """Two independent client replicas edit — the head contains BOTH edits
    immediately after each 200 (synchronous merge under lock, ADR-038)."""
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    art = artifacts.add(make_artifact())
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)

    row = await svc.apply_update(
        cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("hello ")
    )
    assert _head_text(row.state) == "hello "  # read-your-writes after 1st write

    row = await svc.apply_update(
        cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("world")
    )
    merged = _head_text(row.state)
    assert "hello " in merged and "world" in merged
    assert len(merged) == len("hello world")
    assert row.update_count == 2
    assert len(yjs.updates) == 2  # raw updates appended to the log


async def test_apply_update_rejects_garbage() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    art = artifacts.add(make_artifact())
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)

    with pytest.raises(InvalidYjsUpdate):
        await svc.apply_update(
            cell_id=art.cell_id, artifact_id=art.id, update_data=b"not-a-yjs-update"
        )
    assert yjs.updates == []  # nothing appended on rejection


async def test_apply_update_missing_document_404() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    # No envelope at all → the live-envelope guard 404s first (audit P3).
    with pytest.raises(ArtifactNotFound):
        await svc.apply_update(cell_id=uuid4(), artifact_id=uuid4(), update_data=b"")
    # Envelope exists but has no live Yjs doc → the doc-level 404.
    art = artifacts.add(make_artifact())
    with pytest.raises(YjsDocumentNotFound):
        await svc.apply_update(cell_id=art.cell_id, artifact_id=art.id, update_data=b"")


async def test_commit_version_creates_snapshot_version_and_usage() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    art = artifacts.add(make_artifact())
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)
    await svc.apply_update(
        cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("versioned")
    )

    version, snapshot = await svc.commit_version(cell_id=art.cell_id, artifact_id=art.id)

    assert version.version_num == 1
    assert version.storage_kind == "yjs_snapshot"
    assert version.yjs_snapshot_id == snapshot.id
    assert version.byte_size == len(snapshot.state)
    assert _head_text(snapshot.state) == "versioned"
    assert art.current_version_num == 1
    assert usage.by_cell[art.cell_id] == version.byte_size  # AC-01.5.7 accounting


async def test_compaction_prunes_log_never_snapshots() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage, compact_update_count=2)
    art = artifacts.add(make_artifact())
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)

    # Strict ADR-038 threshold: compaction fires only when count EXCEEDS the
    # limit — 2nd update (count == 2) must NOT compact, 3rd (count == 3) must.
    for word in ("a", "b"):
        row = await svc.apply_update(
            cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update(word)
        )
    assert yjs.snapshots == [] and len(yjs.updates) == 2  # == threshold: no compact
    row = await svc.apply_update(
        cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("c")
    )

    assert yjs.updates == []  # log pruned
    assert len(yjs.snapshots) == 1  # compaction snapshot persisted, NOT deleted
    assert row.update_count == 0  # counter reset
    assert row.last_compacted_at is not None
    merged = _head_text(row.state)
    assert sorted(merged) == ["a", "b", "c"]  # state survives compaction

    # Another update after compaction starts a fresh log; snapshots accumulate.
    await svc.apply_update(cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("d"))
    assert len(yjs.updates) == 1
    assert len(yjs.snapshots) == 1


async def test_compaction_triggers_on_state_size() -> None:
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage, compact_state_bytes=10)
    art = artifacts.add(make_artifact())
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)

    await svc.apply_update(
        cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("x" * 64)
    )
    assert len(yjs.snapshots) == 1  # size threshold fired on the first update
    assert yjs.updates == []


async def test_soft_deleted_envelope_yields_404_on_yjs_surface() -> None:
    """Audit P3: get/apply/commit on a soft-deleted artifact behave like resolve — 404."""
    yjs, artifacts, usage = FakeYjsRepo(), FakeArtifactRepo(), FakeUsageRepo()
    svc = _service(yjs, artifacts, usage)
    art = artifacts.add(make_artifact())
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)
    art.deleted_at = art.created_at  # soft-delete the envelope

    with pytest.raises(ArtifactNotFound):
        await svc.get_document(cell_id=art.cell_id, artifact_id=art.id)
    with pytest.raises(ArtifactNotFound):
        await svc.apply_update(
            cell_id=art.cell_id, artifact_id=art.id, update_data=_client_update("x")
        )
    with pytest.raises(ArtifactNotFound):
        await svc.commit_version(cell_id=art.cell_id, artifact_id=art.id)
    assert yjs.updates == [] and yjs.snapshots == []  # nothing written


async def test_create_document_toctou_duplicate_maps_to_409() -> None:
    """Audit P3: a racer inserting between pre-check and INSERT surfaces as the
    409 domain error (UNIQUE(artifact_id) via SAVEPOINT), never a raw 500."""
    artifacts, usage = FakeArtifactRepo(), FakeUsageRepo()
    art = artifacts.add(make_artifact())

    class _BlindYjsRepo(FakeYjsRepo):
        """Pre-check sees nothing → the INSERT's UNIQUE is the only guard."""

        async def get_by_artifact(self, artifact_id: object, *, cell_id: object) -> None:
            return None

    blind = _BlindYjsRepo()
    svc = _service(blind, artifacts, usage)
    await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)
    with pytest.raises(YjsDocumentAlreadyExists):  # 2nd insert hits UNIQUE
        await svc.create_document(cell_id=art.cell_id, artifact_id=art.id)
