"""Envelope + version + usage repository — artifacts.{artifacts,artifact_versions,
cell_storage_usage}.

Version rows are append-only (DB grants deny UPDATE); the race on
``UNIQUE(artifact_id, version_num)`` is surfaced to the service layer as
``IntegrityError`` from ``insert_version`` inside a SAVEPOINT, so the service
can retry with a re-read head without poisoning the outer transaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.artifacts.models import Artifact, ArtifactVersion, CellStorageUsage


class ArtifactRepository:
    """Envelope + versions access, cell-isolated via RLS."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── envelope ────────────────────────────────────────────────────── #

    async def insert(
        self,
        *,
        cell_id: UUID,
        artifact_type: str,
        title: str,
        tags: Sequence[str] | None = None,
        owner_user_id: UUID | None = None,
        created_by_agent_id: UUID | None = None,
    ) -> Artifact:
        row = Artifact(
            cell_id=cell_id,
            artifact_type=artifact_type,
            title=title,
            tags=list(tags or []),
            owner_user_id=owner_user_id,
            created_by_agent_id=created_by_agent_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(
        self, artifact_id: UUID, *, cell_id: UUID, include_deleted: bool = False
    ) -> Artifact | None:
        stmt = select(Artifact).where(Artifact.id == artifact_id, Artifact.cell_id == cell_id)
        if not include_deleted:
            stmt = stmt.where(Artifact.deleted_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_for_update(self, artifact_id: UUID, *, cell_id: UUID) -> Artifact | None:
        """Row-lock the envelope — serializes version numbering per artifact."""
        stmt = (
            select(Artifact)
            .where(
                Artifact.id == artifact_id,
                Artifact.cell_id == cell_id,
                Artifact.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_recent(
        self,
        cell_id: UUID,
        *,
        artifact_type: str | None = None,
        limit: int,
        offset: int = 0,
    ) -> Sequence[Artifact]:
        stmt = (
            select(Artifact)
            .where(Artifact.cell_id == cell_id, Artifact.deleted_at.is_(None))
            .order_by(Artifact.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if artifact_type is not None:
            stmt = stmt.where(Artifact.artifact_type == artifact_type)
        return (await self._session.execute(stmt)).scalars().all()

    async def soft_delete(self, artifact_id: UUID, *, cell_id: UUID) -> bool:
        result = await self._session.execute(
            update(Artifact)
            .where(
                Artifact.id == artifact_id,
                Artifact.cell_id == cell_id,
                Artifact.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
            .returning(Artifact.id)
        )
        return result.scalar_one_or_none() is not None

    async def set_current_version(self, artifact_id: UUID, *, version_num: int) -> None:
        await self._session.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(current_version_num=version_num)
        )

    # ── versions (append-only) ──────────────────────────────────────── #

    async def insert_version(self, **fields: Any) -> ArtifactVersion:
        """INSERT one version row inside a SAVEPOINT.

        Raises ``IntegrityError`` on ``UNIQUE(artifact_id, version_num)``
        violation; the SAVEPOINT keeps the outer transaction usable so the
        caller can re-read the head and retry (AC-01.5.2).
        """
        row = ArtifactVersion(**fields)
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            # Detach the failed instance so a retry inserts a fresh row
            # (the rolled-back SAVEPOINT may have evicted it already).
            if row in self._session:
                self._session.expunge(row)
            raise
        return row

    async def get_version(
        self, artifact_id: UUID, version_num: int, *, cell_id: UUID
    ) -> ArtifactVersion | None:
        stmt = select(ArtifactVersion).where(
            ArtifactVersion.artifact_id == artifact_id,
            ArtifactVersion.version_num == version_num,
            ArtifactVersion.cell_id == cell_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_versions(self, artifact_id: UUID, *, cell_id: UUID) -> Sequence[ArtifactVersion]:
        stmt = (
            select(ArtifactVersion)
            .where(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.cell_id == cell_id,
            )
            .order_by(ArtifactVersion.version_num)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def max_version_num(self, artifact_id: UUID) -> int:
        """Highest committed version_num (0 when none) — race-retry re-read."""
        stmt = select(func.coalesce(func.max(ArtifactVersion.version_num), 0)).where(
            ArtifactVersion.artifact_id == artifact_id
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def sum_version_bytes(self, artifact_id: UUID) -> int:
        stmt = select(func.coalesce(func.sum(ArtifactVersion.byte_size), 0)).where(
            ArtifactVersion.artifact_id == artifact_id
        )
        return int((await self._session.execute(stmt)).scalar_one())


class UsageRepository:
    """artifacts.cell_storage_usage — transactional per-cell bytes accounting."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_bytes(self, cell_id: UUID, delta: int) -> None:
        """UPSERT the counter atomically. Never lets bytes_total go negative
        (a decrement below zero clamps — defensive; CHECK would reject it)."""
        stmt = pg_insert(CellStorageUsage).values(cell_id=cell_id, bytes_total=max(delta, 0))
        stmt = stmt.on_conflict_do_update(
            index_elements=[CellStorageUsage.cell_id],
            set_={
                "bytes_total": func.greatest(CellStorageUsage.bytes_total + delta, 0),
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)

    async def get_bytes(self, cell_id: UUID) -> int:
        stmt = select(CellStorageUsage.bytes_total).where(CellStorageUsage.cell_id == cell_id)
        value = (await self._session.execute(stmt)).scalar_one_or_none()
        return int(value) if value is not None else 0
