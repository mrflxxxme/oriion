"""SQLAlchemy 2.x models for the memory bounded context (ADR-011 Wave-1).

Schema authoritative per ``migrations/versions/memory/*`` — the ORM mirrors the
migration (alembic builds the test/CI schema, NOT ``create_all``). The HNSW
vector index lives in the migration only (not expressible cleanly in ORM
``__table_args__``); the planner uses it automatically for cosine ordering.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Identity, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base

# ── Single source of truth for the embedding dimension ──────────────────── #
# YandexGPT text embeddings (text-search-doc / text-search-query) are 256-dim
# (grill 2026-06-23, Q1). Changing this requires re-embedding + a reindex
# migration AND updating migrations/versions/memory/0001_memory_core.py.
MEMORY_EMBEDDING_DIM = 256

# ── Soft caps (grill Q7) — bound retrieval/cost before UI pagination ─────── #
# Soft = a warning signal on write; entries persist until explicit delete
# (no auto-eviction, no hard reject). Enforced in the service layer.
CELL_MEMORY_SOFT_CAP = 500
ROLE_MEMORY_SOFT_CAP = 200


class MemoryEntry(Base):
    """Cell-level shared memory row — recallable by any agent in the cell."""

    __tablename__ = "memory_entries"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('fact','note','glossary','conversation_summary')",
            name="memory_entries_kind_check",
        ),
        CheckConstraint(
            "source IN ('manual','filter_agent','summary')",
            name="memory_entries_source_check",
        ),
        Index("ix_memory_entries_cell_created", "cell_id", text("created_at DESC")),
        {"schema": "memory"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'fact'"))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(MEMORY_EMBEDDING_DIM), nullable=True
    )
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'manual'"))
    contains_pii: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


class ConversationMessage(Base):
    """One message in a per agent-instance conversation log (ADR-011 Wave-1).

    Immutable + append-only. ``seq`` (IDENTITY) gives stable FIFO ordering even
    when several messages are appended in one transaction (``created_at`` =
    transaction time and would tie).
    """

    __tablename__ = "conversation_history"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user','agent','system')",
            name="conversation_history_role_check",
        ),
        Index("ix_conversation_cell_agent_seq", "cell_id", "agent_id", "seq"),
        {"schema": "memory"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))


class RoleMemoryEntry(Base):
    """Per agent-instance personal memory row — scoped by cell_id (RLS) + agent_id."""

    __tablename__ = "role_memory_entries"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('preference','style','process','fact','note')",
            name="role_memory_entries_kind_check",
        ),
        CheckConstraint(
            "source IN ('manual','filter_agent','summary')",
            name="role_memory_entries_source_check",
        ),
        Index(
            "ix_role_memory_cell_agent_created",
            "cell_id",
            "agent_id",
            text("created_at DESC"),
        ),
        {"schema": "memory"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cell_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'preference'"))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(MEMORY_EMBEDDING_DIM), nullable=True
    )
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'manual'"))
    contains_pii: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
