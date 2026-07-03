"""Unit tests for the artifact:// resolver — strict grammar + 404 semantics.

AC-01.5.5: head + /vN + cell-mismatch→404 (same error as not-found, no
existence oracle) + malformed→422 + dispatch across all three storage kinds.
"""

from __future__ import annotations

import base64
from uuid import UUID, uuid4

import pytest
from src.artifacts.exceptions import (
    ArtifactNotFound,
    ArtifactVersionNotFound,
    MalformedArtifactUrl,
)
from src.artifacts.services.resolver import ArtifactResolver, parse_artifact_url
from src.artifacts.services.s3 import S3AssetService
from src.artifacts.services.yjs import YjsService

from tests.artifacts._fakes import (
    FakeArtifactRepo,
    FakeObjectStorage,
    FakeS3Repo,
    FakeUsageRepo,
    FakeYjsRepo,
    make_artifact,
)

_CELL = UUID("11111111-1111-4111-8111-111111111111")
_ART = UUID("22222222-2222-4222-8222-222222222222")


# ── parse ───────────────────────────────────────────────────────────────── #


def test_parse_head_and_versioned() -> None:
    head = parse_artifact_url(f"artifact://{_CELL}/{_ART}")
    assert (head.cell_id, head.artifact_id, head.version_num) == (_CELL, _ART, None)

    v7 = parse_artifact_url(f"artifact://{_CELL}/{_ART}/v7")
    assert v7.version_num == 7


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "artifact://",
        f"artifact://{_CELL}",  # no artifact id
        f"artifact://{_CELL}/{_ART}/v0",  # versions start at 1
        f"artifact://{_CELL}/{_ART}/v01",  # no leading zeros
        f"artifact://{_CELL}/{_ART}/7",  # missing 'v'
        f"artifact://{_CELL}/{_ART}/v7/extra",  # trailing segment
        # canonical lowercase only (letters, so upper() actually differs)
        f"artifact://ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF/{_ART}",
        f"http://{_CELL}/{_ART}",  # wrong scheme
        f"artifact://{_CELL}/not-a-uuid",
        f"artifact://{_CELL}/{_ART} ",  # trailing junk
        f"artifact://{_CELL}/{_ART}\n",  # trailing newline ($-anchor trap)
    ],
)
def test_parse_malformed_422(bad: str) -> None:
    with pytest.raises(MalformedArtifactUrl):
        parse_artifact_url(bad)


# ── resolve ─────────────────────────────────────────────────────────────── #


def _resolver(
    artifacts: FakeArtifactRepo, yjs: FakeYjsRepo, s3_repo: FakeS3Repo, storage: FakeObjectStorage
) -> ArtifactResolver:
    s3_svc = S3AssetService(
        s3_repo,  # type: ignore[arg-type]
        artifacts,  # type: ignore[arg-type]
        FakeUsageRepo(),  # type: ignore[arg-type]
        storage,
        bucket="b",
        env_prefix="test",
        max_upload_bytes=1024,
    )
    return ArtifactResolver(artifacts, yjs, s3_svc)  # type: ignore[arg-type]


async def test_resolve_head_and_explicit_version_inline() -> None:
    artifacts, yjs, s3_repo, storage = (
        FakeArtifactRepo(),
        FakeYjsRepo(),
        FakeS3Repo(),
        FakeObjectStorage(),
    )
    art = artifacts.add(make_artifact(id=_ART, cell_id=_CELL, current_version_num=2))
    for num, text in ((1, "old"), (2, "new")):
        await artifacts.insert_version(
            cell_id=_CELL,
            artifact_id=art.id,
            version_num=num,
            storage_kind="inline",
            content_inline={"text": text},
            s3_object_id=None,
            yjs_snapshot_id=None,
            byte_size=3,
            content_hash_sha256="h",
        )
    resolver = _resolver(artifacts, yjs, s3_repo, storage)

    head = await resolver.resolve(f"artifact://{_CELL}/{_ART}", current_cell_id=_CELL)
    assert head.version_num == 2 and head.content_inline == {"text": "new"}

    v1 = await resolver.resolve(f"artifact://{_CELL}/{_ART}/v1", current_cell_id=_CELL)
    assert v1.version_num == 1 and v1.content_inline == {"text": "old"}
    assert v1.storage_kind == "inline" and v1.download_url is None


async def test_resolve_cell_mismatch_is_plain_404() -> None:
    artifacts, yjs, s3_repo, storage = (
        FakeArtifactRepo(),
        FakeYjsRepo(),
        FakeS3Repo(),
        FakeObjectStorage(),
    )
    artifacts.add(make_artifact(id=_ART, cell_id=_CELL, current_version_num=1))
    resolver = _resolver(artifacts, yjs, s3_repo, storage)

    other_cell = uuid4()
    with pytest.raises(ArtifactNotFound) as mismatch:
        await resolver.resolve(f"artifact://{_CELL}/{_ART}", current_cell_id=other_cell)
    with pytest.raises(ArtifactNotFound) as missing:
        await resolver.resolve(f"artifact://{other_cell}/{uuid4()}", current_cell_id=other_cell)
    # Same code + status: a foreign cell cannot distinguish existence (G2).
    assert mismatch.value.code == missing.value.code == "artifacts.not_found"
    assert mismatch.value.status_code == missing.value.status_code == 404


async def test_resolve_head_with_zero_versions_404() -> None:
    artifacts, yjs, s3_repo, storage = (
        FakeArtifactRepo(),
        FakeYjsRepo(),
        FakeS3Repo(),
        FakeObjectStorage(),
    )
    artifacts.add(make_artifact(id=_ART, cell_id=_CELL))
    resolver = _resolver(artifacts, yjs, s3_repo, storage)

    with pytest.raises(ArtifactVersionNotFound):
        await resolver.resolve(f"artifact://{_CELL}/{_ART}", current_cell_id=_CELL)
    with pytest.raises(ArtifactVersionNotFound):
        await resolver.resolve(f"artifact://{_CELL}/{_ART}/v5", current_cell_id=_CELL)


async def test_resolve_s3_version_returns_signed_url() -> None:
    artifacts, yjs, s3_repo, storage = (
        FakeArtifactRepo(),
        FakeYjsRepo(),
        FakeS3Repo(),
        FakeObjectStorage(),
    )
    art = artifacts.add(make_artifact(id=_ART, cell_id=_CELL, artifact_type="asset"))
    obj = await s3_repo.insert_pending(
        cell_id=_CELL, artifact_id=art.id, bucket="b", s3_key="test/k/pic.png"
    )
    await s3_repo.mark_stored(obj.id, byte_size=4, content_hash_sha256="h")
    await artifacts.insert_version(
        cell_id=_CELL,
        artifact_id=art.id,
        version_num=1,
        storage_kind="s3",
        content_inline=None,
        s3_object_id=obj.id,
        yjs_snapshot_id=None,
        byte_size=4,
        content_hash_sha256="h",
    )
    art.current_version_num = 1
    resolver = _resolver(artifacts, yjs, s3_repo, storage)

    resolved = await resolver.resolve(f"artifact://{_CELL}/{_ART}", current_cell_id=_CELL)
    assert resolved.storage_kind == "s3"
    assert resolved.download_url is not None and "signed=1" in resolved.download_url
    assert resolved.content_inline is None and resolved.yjs_state_base64 is None


async def test_resolve_yjs_snapshot_version_returns_state() -> None:
    artifacts, yjs, s3_repo, storage = (
        FakeArtifactRepo(),
        FakeYjsRepo(),
        FakeS3Repo(),
        FakeObjectStorage(),
    )
    art = artifacts.add(make_artifact(id=_ART, cell_id=_CELL))
    yjs_svc = YjsService(yjs, artifacts, FakeUsageRepo())  # type: ignore[arg-type]
    await yjs_svc.create_document(cell_id=_CELL, artifact_id=art.id)
    version, snapshot = await yjs_svc.commit_version(cell_id=_CELL, artifact_id=art.id)
    resolver = _resolver(artifacts, yjs, s3_repo, storage)

    resolved = await resolver.resolve(
        f"artifact://{_CELL}/{_ART}/v{version.version_num}", current_cell_id=_CELL
    )
    assert resolved.storage_kind == "yjs_snapshot"
    assert resolved.yjs_state_base64 is not None
    assert base64.b64decode(resolved.yjs_state_base64) == snapshot.state
