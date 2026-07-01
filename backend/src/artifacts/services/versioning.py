"""Version allocation — the single write path for artifact_versions rows.

ADR-038 mechanics: version numbering is serialized by a FOR-UPDATE lock on
the envelope; ``UNIQUE(artifact_id, version_num)`` remains the authoritative
guard, so a direct-SQL racer still surfaces as IntegrityError and the loop
retries with a re-read head (AC-01.5.2). Every committed version increments
``cell_storage_usage.bytes_total`` transactionally (AC-01.5.7) and emits
``oriion.artifacts.version_created.v1`` (AC-01.5.8).
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError

from src.artifacts.events import emit_artifact_version_created
from src.artifacts.exceptions import ArtifactNotFound, VersionConflict
from src.artifacts.models import ArtifactVersion
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository

logger = structlog.get_logger(__name__)

_MAX_ATTEMPTS = 3


async def allocate_version(
    artifact_repo: ArtifactRepository,
    usage_repo: UsageRepository,
    *,
    cell_id: UUID,
    artifact_id: UUID,
    storage_kind: str,
    byte_size: int,
    content_hash_sha256: str,
    content_inline: dict[str, object] | None = None,
    s3_object_id: UUID | None = None,
    yjs_snapshot_id: UUID | None = None,
    text_export: str | None = None,
    created_by_user_id: UUID | None = None,
    created_by_agent_id: UUID | None = None,
) -> ArtifactVersion:
    """Insert the next append-only version row + bump the envelope head.

    Raises ``ArtifactNotFound`` when the envelope is absent/soft-deleted and
    ``VersionConflict`` when the UNIQUE race persists after retries.
    """
    envelope = await artifact_repo.get_for_update(artifact_id, cell_id=cell_id)
    if envelope is None:
        raise ArtifactNotFound(str(artifact_id))

    next_num = envelope.current_version_num + 1
    version: ArtifactVersion | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            version = await artifact_repo.insert_version(
                cell_id=cell_id,
                artifact_id=artifact_id,
                version_num=next_num,
                storage_kind=storage_kind,
                content_inline=content_inline,
                s3_object_id=s3_object_id,
                yjs_snapshot_id=yjs_snapshot_id,
                byte_size=byte_size,
                content_hash_sha256=content_hash_sha256,
                text_export=text_export,
                created_by_user_id=created_by_user_id,
                created_by_agent_id=created_by_agent_id,
            )
            break
        except IntegrityError as exc:
            logger.warning(
                "artifacts.version.race_retry",
                context="artifacts",
                action="allocate_version",
                artifact_id=str(artifact_id),
                attempted_num=next_num,
                attempt=attempt,
                error_type=type(exc.orig).__name__,
                error=str(exc.orig),
            )
            next_num = await artifact_repo.max_version_num(artifact_id) + 1
    if version is None:
        raise VersionConflict(str(artifact_id))

    await artifact_repo.set_current_version(artifact_id, version_num=next_num)
    if byte_size > 0:
        await usage_repo.add_bytes(cell_id, byte_size)
    await emit_artifact_version_created(
        artifact_id=artifact_id,
        cell_id=cell_id,
        version_num=next_num,
        storage_kind=storage_kind,
        byte_size=byte_size,
    )
    return version
