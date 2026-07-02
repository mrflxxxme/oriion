"""S3 objects repository — artifacts.s3_objects lifecycle rows.

``insert_pending`` runs inside a SAVEPOINT so the ``UNIQUE(bucket, s3_key)``
transactional key reservation (ADR-038 graft G3) surfaces as ``IntegrityError``
without poisoning the outer transaction.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.artifacts.models import S3Object


class S3ObjectRepository:
    """Lifecycle access: pending → stored → deleted."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_pending(
        self,
        *,
        cell_id: UUID,
        artifact_id: UUID,
        bucket: str,
        s3_key: str,
        mime_type: str | None = None,
    ) -> S3Object:
        """Reserve the key transactionally. Raises ``IntegrityError`` when the
        (bucket, s3_key) pair is already reserved — caller maps it to 409."""
        row = S3Object(
            cell_id=cell_id,
            artifact_id=artifact_id,
            bucket=bucket,
            s3_key=s3_key,
            mime_type=mime_type,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            # The rolled-back SAVEPOINT may have evicted the instance already.
            if row in self._session:
                self._session.expunge(row)
            raise
        return row

    async def get(self, s3_object_id: UUID, *, cell_id: UUID) -> S3Object | None:
        stmt = select(S3Object).where(S3Object.id == s3_object_id, S3Object.cell_id == cell_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find_stored_by_key(self, s3_key: str, *, cell_id: UUID) -> S3Object | None:
        """Resolve a bare key (e.g. ``tasks.task_artifacts.s3_key``) to its
        lifecycle row. Only ``stored`` objects resolve — pending/deleted don't."""
        stmt = select(S3Object).where(
            S3Object.s3_key == s3_key,
            S3Object.cell_id == cell_id,
            S3Object.status == "stored",
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def mark_stored(
        self, s3_object_id: UUID, *, byte_size: int, content_hash_sha256: str
    ) -> bool:
        """Conditional lifecycle transition ``pending → stored``.

        The ``status = 'pending'`` predicate is the concurrency arbiter (audit
        P1): of two overlapping completes exactly one matches the row and wins;
        the loser gets ``False`` and must NOT allocate a version or count usage.
        """
        result = await self._session.execute(
            update(S3Object)
            .where(S3Object.id == s3_object_id, S3Object.status == "pending")
            .values(
                status="stored",
                byte_size=byte_size,
                content_hash_sha256=content_hash_sha256,
            )
            .returning(S3Object.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_deleted(self, s3_object_id: UUID) -> None:
        await self._session.execute(
            update(S3Object).where(S3Object.id == s3_object_id).values(status="deleted")
        )

    async def mark_all_deleted_for_artifact(self, artifact_id: UUID, *, cell_id: UUID) -> int:
        """Flip every non-deleted lifecycle row of the artifact to ``deleted``
        (envelope soft-delete). Physical S3 removal is the janitor's job."""
        result = await self._session.execute(
            update(S3Object)
            .where(
                S3Object.artifact_id == artifact_id,
                S3Object.cell_id == cell_id,
                S3Object.status != "deleted",
            )
            .values(status="deleted")
            .returning(S3Object.id)
        )
        return len(result.scalars().all())

    async def delete_stale_pending(self, *, cell_id: UUID, older_than: datetime) -> int:
        """Janitor: drop ``pending`` reservations whose presign window expired.
        Returns the number of pruned rows."""
        result = await self._session.execute(
            delete(S3Object)
            .where(
                S3Object.cell_id == cell_id,
                S3Object.status == "pending",
                S3Object.created_at < older_than,
            )
            .returning(S3Object.id)
        )
        return len(result.scalars().all())
