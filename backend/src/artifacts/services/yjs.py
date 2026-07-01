"""Yjs document service — pycrdt merge under FOR UPDATE (ADR-038).

Write path (synchronous merge, read-your-writes): lock the yjs_documents row
FOR UPDATE → append the raw update to the log → pycrdt-merge into ``state`` +
refresh ``state_vector`` → flush. A GET after the 200 always returns the
merged head.

Compaction: when the log grew past ``YJS_COMPACT_UPDATE_COUNT`` entries or the
merged state exceeds ``YJS_COMPACT_STATE_BYTES``, take a snapshot of the head
and prune the log up to the highest pruned seq — snapshots are NEVER deleted
(AC-01.5.3).

Version = explicit commit: head state → yjs_snapshots row + an immutable
``artifact_versions(storage_kind='yjs_snapshot')`` row via ``allocate_version``.
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

import structlog
from pycrdt import Doc

from src.artifacts.events import emit_yjs_snapshot_committed
from src.artifacts.exceptions import (
    ArtifactNotFound,
    ArtifactTypeMismatch,
    InvalidYjsUpdate,
    YjsDocumentAlreadyExists,
    YjsDocumentNotFound,
)
from src.artifacts.models import (
    YJS_COMPACT_STATE_BYTES,
    YJS_COMPACT_UPDATE_COUNT,
    ArtifactVersion,
    YjsDocument,
    YjsSnapshot,
)
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository
from src.artifacts.repositories.yjs_repository import YjsRepository
from src.artifacts.services.versioning import allocate_version

logger = structlog.get_logger(__name__)


class YjsService:
    """Live CRDT head lifecycle: create / merge / commit / compact."""

    def __init__(
        self,
        yjs_repo: YjsRepository,
        artifact_repo: ArtifactRepository,
        usage_repo: UsageRepository,
        *,
        compact_update_count: int = YJS_COMPACT_UPDATE_COUNT,
        compact_state_bytes: int = YJS_COMPACT_STATE_BYTES,
    ) -> None:
        self._yjs_repo = yjs_repo
        self._artifact_repo = artifact_repo
        self._usage_repo = usage_repo
        self._compact_update_count = compact_update_count
        self._compact_state_bytes = compact_state_bytes

    async def create_document(self, *, cell_id: UUID, artifact_id: UUID) -> YjsDocument:
        """Create the live CRDT head for a 'document'/'code' artifact."""
        artifact = await self._artifact_repo.get(artifact_id, cell_id=cell_id)
        if artifact is None:
            raise ArtifactNotFound(str(artifact_id))
        if artifact.artifact_type not in ("document", "code"):
            raise ArtifactTypeMismatch(
                f"yjs documents apply to 'document'/'code' artifacts, "
                f"not '{artifact.artifact_type}'"
            )
        if await self._yjs_repo.get_by_artifact(artifact_id, cell_id=cell_id) is not None:
            raise YjsDocumentAlreadyExists(str(artifact_id))
        empty: Doc[Any] = Doc()
        return await self._yjs_repo.insert_document(
            cell_id=cell_id,
            artifact_id=artifact_id,
            state=empty.get_update(),
            state_vector=empty.get_state(),
        )

    async def get_document(self, *, cell_id: UUID, artifact_id: UUID) -> YjsDocument:
        row = await self._yjs_repo.get_by_artifact(artifact_id, cell_id=cell_id)
        if row is None:
            raise YjsDocumentNotFound(str(artifact_id))
        return row

    async def apply_update(
        self, *, cell_id: UUID, artifact_id: UUID, update_data: bytes
    ) -> YjsDocument:
        """Merge one client update into the head under the row lock."""
        row = await self._yjs_repo.get_by_artifact_for_update(artifact_id, cell_id=cell_id)
        if row is None:
            raise YjsDocumentNotFound(str(artifact_id))

        doc: Doc[Any] = Doc()
        doc.apply_update(row.state)  # rebuild the head; trusted bytes
        try:
            doc.apply_update(update_data)
        except ValueError as exc:
            raise InvalidYjsUpdate(f"undecodable yjs update: {exc}") from exc

        new_state = doc.get_update()
        new_vector = doc.get_state()
        await self._yjs_repo.append_update(
            document_id=row.id, cell_id=cell_id, update_data=update_data
        )
        await self._yjs_repo.save_head(
            row,
            state=new_state,
            state_vector=new_vector,
            update_count=row.update_count + 1,
        )
        if (
            row.update_count >= self._compact_update_count
            or len(new_state) > self._compact_state_bytes
        ):
            await self._compact(row)
        return row

    async def commit_version(
        self,
        *,
        cell_id: UUID,
        artifact_id: UUID,
        created_by_user_id: UUID | None = None,
        created_by_agent_id: UUID | None = None,
    ) -> tuple[ArtifactVersion, YjsSnapshot]:
        """Explicit commit: freeze the head into an immutable snapshot + version."""
        row = await self._yjs_repo.get_by_artifact_for_update(artifact_id, cell_id=cell_id)
        if row is None:
            raise YjsDocumentNotFound(str(artifact_id))

        snapshot = await self._yjs_repo.insert_snapshot(
            document_id=row.id,
            cell_id=cell_id,
            state=row.state,
            state_vector=row.state_vector,
        )
        version = await allocate_version(
            self._artifact_repo,
            self._usage_repo,
            cell_id=cell_id,
            artifact_id=artifact_id,
            storage_kind="yjs_snapshot",
            yjs_snapshot_id=snapshot.id,
            byte_size=len(row.state),
            content_hash_sha256=hashlib.sha256(row.state).hexdigest(),
            created_by_user_id=created_by_user_id,
            created_by_agent_id=created_by_agent_id,
        )
        await emit_yjs_snapshot_committed(
            artifact_id=artifact_id,
            cell_id=cell_id,
            yjs_document_id=row.id,
            snapshot_id=snapshot.id,
            version_num=version.version_num,
            byte_size=version.byte_size,
        )
        return version, snapshot

    async def _compact(self, row: YjsDocument) -> None:
        """Snapshot the head, prune the log up to its current max seq.

        Compaction NEVER deletes snapshots — only yjs_updates rows.
        """
        await self._yjs_repo.insert_snapshot(
            document_id=row.id,
            cell_id=row.cell_id,
            state=row.state,
            state_vector=row.state_vector,
        )
        max_seq = await self._yjs_repo.max_update_seq(row.id)
        pruned = 0
        if max_seq is not None:
            pruned = await self._yjs_repo.prune_updates(row.id, up_to_seq=max_seq)
        await self._yjs_repo.mark_compacted(row)
        logger.info(
            "artifacts.yjs.compacted",
            context="artifacts",
            action="compact",
            yjs_document_id=str(row.id),
            pruned_updates=pruned,
            state_bytes=len(row.state),
        )
