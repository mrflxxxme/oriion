"""Yjs repository — artifacts.{yjs_documents,yjs_updates,yjs_snapshots}.

The FOR-UPDATE row lock on ``yjs_documents`` is the ADR-038 write-path
serializer: every REST update merges under the lock so a GET after a 200
always sees the merged state (read-your-writes). Snapshots are immutable
(DB grants deny UPDATE/DELETE); compaction prunes ONLY the update log.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.artifacts.models import YjsDocument, YjsSnapshot, YjsUpdate


class YjsRepository:
    """Live head + append log + snapshot history access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── documents ───────────────────────────────────────────────────── #

    async def insert_document(
        self,
        *,
        cell_id: UUID,
        artifact_id: UUID,
        state: bytes,
        state_vector: bytes,
    ) -> YjsDocument:
        row = YjsDocument(
            cell_id=cell_id,
            artifact_id=artifact_id,
            state=state,
            state_vector=state_vector,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_artifact(self, artifact_id: UUID, *, cell_id: UUID) -> YjsDocument | None:
        stmt = select(YjsDocument).where(
            YjsDocument.artifact_id == artifact_id, YjsDocument.cell_id == cell_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, document_id: UUID, *, cell_id: UUID) -> YjsDocument | None:
        stmt = select(YjsDocument).where(
            YjsDocument.id == document_id, YjsDocument.cell_id == cell_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_artifact_for_update(
        self, artifact_id: UUID, *, cell_id: UUID
    ) -> YjsDocument | None:
        """FOR UPDATE row lock — the ADR-038 synchronous-merge serializer."""
        stmt = (
            select(YjsDocument)
            .where(YjsDocument.artifact_id == artifact_id, YjsDocument.cell_id == cell_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def save_head(
        self,
        row: YjsDocument,
        *,
        state: bytes,
        state_vector: bytes,
        update_count: int,
    ) -> None:
        """Persist the merged head onto the (locked) ORM instance so the caller
        returns fresh values without a re-read."""
        row.state = state
        row.state_vector = state_vector
        row.update_count = update_count
        await self._session.flush()

    async def mark_compacted(self, row: YjsDocument) -> None:
        row.update_count = 0
        row.last_compacted_at = datetime.now(UTC)
        await self._session.flush()

    # ── update log ──────────────────────────────────────────────────── #

    async def append_update(
        self, *, document_id: UUID, cell_id: UUID, update_data: bytes
    ) -> YjsUpdate:
        row = YjsUpdate(cell_id=cell_id, yjs_document_id=document_id, update_data=update_data)
        self._session.add(row)
        await self._session.flush()
        return row

    async def count_updates(self, document_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(YjsUpdate)
            .where(YjsUpdate.yjs_document_id == document_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def prune_updates(self, document_id: UUID, *, up_to_seq: int) -> int:
        """DELETE log entries with ``seq <= up_to_seq`` — compaction prunes the
        log only, never snapshots (AC-01.5.3). Returns the pruned row count."""
        result = await self._session.execute(
            delete(YjsUpdate)
            .where(YjsUpdate.yjs_document_id == document_id, YjsUpdate.seq <= up_to_seq)
            .returning(YjsUpdate.seq)
        )
        return len(result.scalars().all())

    async def max_update_seq(self, document_id: UUID) -> int | None:
        stmt = select(func.max(YjsUpdate.seq)).where(YjsUpdate.yjs_document_id == document_id)
        value = (await self._session.execute(stmt)).scalar_one_or_none()
        return int(value) if value is not None else None

    # ── snapshots (immutable) ───────────────────────────────────────── #

    async def insert_snapshot(
        self,
        *,
        document_id: UUID,
        cell_id: UUID,
        state: bytes,
        state_vector: bytes,
    ) -> YjsSnapshot:
        row = YjsSnapshot(
            cell_id=cell_id,
            yjs_document_id=document_id,
            state=state,
            state_vector=state_vector,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_snapshot(self, snapshot_id: UUID, *, cell_id: UUID) -> YjsSnapshot | None:
        stmt = select(YjsSnapshot).where(
            YjsSnapshot.id == snapshot_id, YjsSnapshot.cell_id == cell_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_snapshots(self, document_id: UUID, *, cell_id: UUID) -> Sequence[YjsSnapshot]:
        stmt = (
            select(YjsSnapshot)
            .where(YjsSnapshot.yjs_document_id == document_id, YjsSnapshot.cell_id == cell_id)
            .order_by(YjsSnapshot.created_at.desc())
        )
        return (await self._session.execute(stmt)).scalars().all()
