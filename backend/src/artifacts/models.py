"""SQLAlchemy 2.x models for the artifacts bounded context (ADR-038, Phase 01.5).

Schema authoritative per ``migrations/versions/artifacts/0001_artifacts_core.py``
— the ORM mirrors the migration (alembic builds the test/CI schema, NOT
``create_all``). Cross-table FKs, composite anti-drift FKs, RLS policies and
immutability grants live in the migration only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Identity, Index, Integer, LargeBinary, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base

# ── Yjs compaction thresholds (ADR-038) — single source of truth ─────────── #
# Compaction (snapshot + update-log prune) triggers when the append log grew
# past YJS_COMPACT_UPDATE_COUNT updates OR the merged state exceeds
# YJS_COMPACT_STATE_BYTES. Compaction NEVER deletes snapshots (AC-01.5.3).
YJS_COMPACT_UPDATE_COUNT: Final[int] = 500
YJS_COMPACT_STATE_BYTES: Final[int] = 1 * 1024 * 1024  # 1 MiB

# ── S3 presign TTLs (ADR-012) ────────────────────────────────────────────── #
PRESIGN_POST_TTL_SECONDS: Final[int] = 5 * 60  # presigned POST upload window
SIGNED_GET_TTL_SECONDS: Final[int] = 60 * 60  # signed download link


class Artifact(Base):
    """Artifact envelope — head pointer ``current_version_num`` + soft-delete."""

    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('document','code','asset')",
            name="artifacts_artifact_type_check",
        ),
        Index("ix_artifacts_cell_created", "cell_id", sa_text("created_at DESC")),
        {"schema": "artifacts"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'[]'::jsonb")
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_by_agent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    current_version_num: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sa_text("0")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))


class ArtifactVersion(Base):
    """Append-only immutable version row — target of ``artifact://.../vN``."""

    __tablename__ = "artifact_versions"
    __table_args__ = (
        CheckConstraint(
            "storage_kind IN ('inline','s3','yjs_snapshot')",
            name="artifact_versions_storage_kind_check",
        ),
        Index(
            "ix_artifact_versions_artifact",
            "artifact_id",
            sa_text("version_num DESC"),
        ),
        {"schema": "artifacts"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_kind: Mapped[str] = mapped_column(Text, nullable=False)
    # none_as_null: Python None must become SQL NULL (not 'null'::jsonb) —
    # the storage_kind XOR CHECK tests `content_inline IS NULL` for s3/yjs rows.
    content_inline: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    s3_object_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    yjs_snapshot_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=sa_text("0"))
    content_hash_sha256: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=sa_text("''")
    )
    text_export: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_by_agent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))


class YjsDocument(Base):
    """Live Yjs CRDT head — merged synchronously under FOR UPDATE."""

    __tablename__ = "yjs_documents"
    __table_args__ = ({"schema": "artifacts"},)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, unique=True)
    state: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    state_vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    update_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa_text("0"))
    last_compacted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))


class YjsUpdate(Base):
    """Append-log entry — pruned by compaction, never authoritative for state."""

    __tablename__ = "yjs_updates"
    __table_args__ = (
        Index("ix_yjs_updates_document_seq", "yjs_document_id", "seq"),
        {"schema": "artifacts"},
    )

    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    yjs_document_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    update_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))


class YjsSnapshot(Base):
    """Immutable point-in-time snapshot — referenced by yjs_snapshot versions."""

    __tablename__ = "yjs_snapshots"
    __table_args__ = (
        Index(
            "ix_yjs_snapshots_document_created",
            "yjs_document_id",
            sa_text("created_at DESC"),
        ),
        {"schema": "artifacts"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    yjs_document_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    state: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    state_vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))


class S3Object(Base):
    """S3 object lifecycle row — ``pending`` (reserved key) → ``stored`` → ``deleted``."""

    __tablename__ = "s3_objects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','stored','deleted')",
            name="s3_objects_status_check",
        ),
        Index("ix_s3_objects_key", "s3_key"),
        Index("ix_s3_objects_artifact", "artifact_id"),
        {"schema": "artifacts"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    bucket: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_hash_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=sa_text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))


class CellStorageUsage(Base):
    """Per-cell stored-bytes accounting (quota enforcement = billing follow-up)."""

    __tablename__ = "cell_storage_usage"
    __table_args__ = ({"schema": "artifacts"},)

    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    bytes_total: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=sa_text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=sa_text("now()"))
