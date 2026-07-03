"""Envelope service — create / list / inline versions / soft-delete / usage.

Soft-delete (ADR-038): the envelope gets ``deleted_at`` (versions stay in the
DB — they are immutable), the artifact disappears from list/get/resolve, its
S3 lifecycle rows flip to ``deleted`` and the cell usage counter is decremented
by the sum of version bytes (logical quota accounting per RQ-20260701-002).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from uuid import UUID

import structlog

from src.artifacts.events import emit_artifact_created, emit_artifact_deleted
from src.artifacts.exceptions import ArtifactNotFound, ArtifactVersionNotFound
from src.artifacts.models import Artifact, ArtifactVersion
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository
from src.artifacts.repositories.s3_repository import S3ObjectRepository
from src.artifacts.services.versioning import allocate_version

logger = structlog.get_logger(__name__)


def _canonical_json(content: dict[str, object]) -> bytes:
    """Deterministic serialization — the hashed/measured representation."""
    return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


class ArtifactService:
    """Envelope lifecycle, cell-isolated via RLS."""

    def __init__(
        self,
        artifact_repo: ArtifactRepository,
        usage_repo: UsageRepository,
        s3_repo: S3ObjectRepository,
    ) -> None:
        self._artifact_repo = artifact_repo
        self._usage_repo = usage_repo
        self._s3_repo = s3_repo

    async def create(
        self,
        *,
        cell_id: UUID,
        artifact_type: str,
        title: str,
        tags: Sequence[str] | None = None,
        owner_user_id: UUID | None = None,
        created_by_agent_id: UUID | None = None,
    ) -> Artifact:
        artifact = await self._artifact_repo.insert(
            cell_id=cell_id,
            artifact_type=artifact_type,
            title=title,
            tags=tags,
            owner_user_id=owner_user_id,
            created_by_agent_id=created_by_agent_id,
        )
        await emit_artifact_created(
            artifact_id=artifact.id,
            cell_id=cell_id,
            artifact_type=artifact_type,
            title=title,
            owner_user_id=owner_user_id,
            created_by_agent_id=created_by_agent_id,
        )
        return artifact

    async def get(self, *, cell_id: UUID, artifact_id: UUID) -> Artifact:
        artifact = await self._artifact_repo.get(artifact_id, cell_id=cell_id)
        if artifact is None:
            raise ArtifactNotFound(str(artifact_id))
        return artifact

    async def list(
        self,
        *,
        cell_id: UUID,
        artifact_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Artifact]:
        return await self._artifact_repo.list_recent(
            cell_id, artifact_type=artifact_type, limit=limit, offset=offset
        )

    async def create_inline_version(
        self,
        *,
        cell_id: UUID,
        artifact_id: UUID,
        content: dict[str, object],
        text_export: str | None = None,
        created_by_user_id: UUID | None = None,
        created_by_agent_id: UUID | None = None,
    ) -> ArtifactVersion:
        body = _canonical_json(content)
        return await allocate_version(
            self._artifact_repo,
            self._usage_repo,
            cell_id=cell_id,
            artifact_id=artifact_id,
            storage_kind="inline",
            content_inline=content,
            byte_size=len(body),
            content_hash_sha256=hashlib.sha256(body).hexdigest(),
            text_export=text_export,
            created_by_user_id=created_by_user_id,
            created_by_agent_id=created_by_agent_id,
        )

    async def get_version(
        self, *, cell_id: UUID, artifact_id: UUID, version_num: int
    ) -> ArtifactVersion:
        version = await self._artifact_repo.get_version(artifact_id, version_num, cell_id=cell_id)
        if version is None:
            raise ArtifactVersionNotFound(str(artifact_id), version_num)
        return version

    async def list_versions(self, *, cell_id: UUID, artifact_id: UUID) -> Sequence[ArtifactVersion]:
        # 404 for an unknown envelope beats an empty list (no existence oracle).
        await self.get(cell_id=cell_id, artifact_id=artifact_id)
        return await self._artifact_repo.list_versions(artifact_id, cell_id=cell_id)

    async def soft_delete(self, *, cell_id: UUID, artifact_id: UUID) -> None:
        # Lock the envelope FIRST (audit P2): allocate_version serializes on
        # the same FOR-UPDATE row lock, so the byte sum + decrement below can
        # never interleave with a concurrent version commit and drift
        # cell_storage_usage.
        envelope = await self._artifact_repo.get_for_update(artifact_id, cell_id=cell_id)
        if envelope is None:
            raise ArtifactNotFound(str(artifact_id))
        bytes_freed = await self._artifact_repo.sum_version_bytes(artifact_id)
        deleted = await self._artifact_repo.soft_delete(artifact_id, cell_id=cell_id)
        if not deleted:  # unreachable while we hold the lock; defensive
            raise ArtifactNotFound(str(artifact_id))
        await self._s3_repo.mark_all_deleted_for_artifact(artifact_id, cell_id=cell_id)
        if bytes_freed > 0:
            await self._usage_repo.add_bytes(cell_id, -bytes_freed)
        await emit_artifact_deleted(
            artifact_id=artifact_id, cell_id=cell_id, bytes_freed=bytes_freed
        )
        logger.info(
            "artifacts.soft_deleted",
            context="artifacts",
            action="soft_delete",
            artifact_id=str(artifact_id),
            cell_id=str(cell_id),
            bytes_freed=bytes_freed,
        )

    async def usage_bytes(self, *, cell_id: UUID) -> int:
        return await self._usage_repo.get_bytes(cell_id)
