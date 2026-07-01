"""Unit tests for allocate_version — numbering, race-retry, usage, events."""

from __future__ import annotations

from uuid import uuid4

import pytest
import structlog.testing
from src.artifacts.exceptions import ArtifactNotFound, VersionConflict
from src.artifacts.services.versioning import allocate_version

from tests.artifacts._fakes import FakeArtifactRepo, FakeUsageRepo, make_artifact


async def test_first_version_is_v1_and_bumps_head() -> None:
    artifacts, usage = FakeArtifactRepo(), FakeUsageRepo()
    art = artifacts.add(make_artifact())

    version = await allocate_version(
        artifacts,  # type: ignore[arg-type]
        usage,  # type: ignore[arg-type]
        cell_id=art.cell_id,
        artifact_id=art.id,
        storage_kind="inline",
        content_inline={"text": "hi"},
        byte_size=2,
        content_hash_sha256="ab" * 32,
    )
    assert version.version_num == 1
    assert art.current_version_num == 1
    assert usage.by_cell[art.cell_id] == 2


async def test_race_retry_reallocates_from_max_version(  # AC-01.5.2
) -> None:
    artifacts, usage = FakeArtifactRepo(), FakeUsageRepo()
    art = artifacts.add(make_artifact(current_version_num=1))
    # A racer already committed v2 behind our back (head still says 1).
    await artifacts.insert_version(
        cell_id=art.cell_id,
        artifact_id=art.id,
        version_num=2,
        storage_kind="inline",
        content_inline={},
        byte_size=0,
        content_hash_sha256="",
    )

    version = await allocate_version(
        artifacts,  # type: ignore[arg-type]
        usage,  # type: ignore[arg-type]
        cell_id=art.cell_id,
        artifact_id=art.id,
        storage_kind="inline",
        content_inline={"text": "retry"},
        byte_size=5,
        content_hash_sha256="cd" * 32,
    )
    assert version.version_num == 3  # 1st attempt (v2) collided → re-read → v3
    assert artifacts.insert_version_calls == 3  # setup insert + collision + retry
    assert art.current_version_num == 3


async def test_persistent_conflict_raises_409() -> None:
    artifacts, usage = FakeArtifactRepo(), FakeUsageRepo()
    art = artifacts.add(make_artifact())
    artifacts.fail_next_inserts = 5  # more than _MAX_ATTEMPTS

    with pytest.raises(VersionConflict):
        await allocate_version(
            artifacts,  # type: ignore[arg-type]
            usage,  # type: ignore[arg-type]
            cell_id=art.cell_id,
            artifact_id=art.id,
            storage_kind="inline",
            content_inline={},
            byte_size=0,
            content_hash_sha256="",
        )
    assert usage.calls == []  # no accounting on failure


async def test_missing_or_deleted_envelope_raises_404() -> None:
    artifacts, usage = FakeArtifactRepo(), FakeUsageRepo()
    with pytest.raises(ArtifactNotFound):
        await allocate_version(
            artifacts,  # type: ignore[arg-type]
            usage,  # type: ignore[arg-type]
            cell_id=uuid4(),
            artifact_id=uuid4(),
            storage_kind="inline",
            content_inline={},
            byte_size=0,
            content_hash_sha256="",
        )


async def test_zero_byte_version_skips_usage_but_emits_event() -> None:
    artifacts, usage = FakeArtifactRepo(), FakeUsageRepo()
    art = artifacts.add(make_artifact())

    with structlog.testing.capture_logs() as logs:
        await allocate_version(
            artifacts,  # type: ignore[arg-type]
            usage,  # type: ignore[arg-type]
            cell_id=art.cell_id,
            artifact_id=art.id,
            storage_kind="inline",
            content_inline={},
            byte_size=0,
            content_hash_sha256="",
        )
    assert usage.calls == []
    ce_types = [entry.get("ce_type") for entry in logs if entry.get("cloudevent")]
    assert "oriion.artifacts.version_created.v1" in ce_types  # AC-01.5.8
