"""SQLAlchemy models for tasks bounded context."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base


def _uuid_pk() -> Mapped[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def _ts_default_now() -> Mapped[datetime]:
    return mapped_column(server_default=text("now()"), nullable=False)


class Task(Base):
    """Top-level agent-team execution unit."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','waiting_input','succeeded','failed',"
            "'cancelled','timed_out')",
            name="tasks_status_chk",
        ),
        Index("idx_tasks_cell_status_time", "cell_id", "status", "created_at"),
        Index(
            "idx_tasks_parent",
            "parent_task_id",
            postgresql_where=text("parent_task_id IS NOT NULL"),
        ),
        {"schema": "tasks"},
    )

    id: Mapped[UUID] = _uuid_pk()
    cell_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("multitenancy.cells.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_instance_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.agent_instances.id"),
        nullable=True,
    )
    team_preset_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    parent_task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    initiated_by_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    input_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'queued'"))
    priority: Mapped[int] = mapped_column(nullable=False, server_default=text("5"))
    # Set when POST /run enqueues the Dramatiq dispatch actor; status stays
    # 'queued' until the worker flips it to 'running' (AC-W1-16a, ADR-034).
    dispatched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_cost_credits: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=text("0")
    )
    total_input_tokens: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    total_output_tokens: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()


class TaskStep(Base):
    __tablename__ = "task_steps"
    __table_args__ = (
        CheckConstraint(
            "step_type IN ('llm_call','tool_use','user_input','wait','branch','merge','delegation')",
            name="task_steps_type_chk",
        ),
        UniqueConstraint("task_id", "step_index", name="task_steps_unique_index"),
        {"schema": "tasks"},
    )

    id: Mapped[UUID] = _uuid_pk()
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_index: Mapped[int] = mapped_column(nullable=False)
    agent_archetype_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.agent_archetypes.id"),
        nullable=False,
    )
    step_type: Mapped[str] = mapped_column(Text, nullable=False)
    input_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    output_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'queued'"))
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cost_credits: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, server_default=text("0")
    )
    error_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class TaskArtifact(Base):
    __tablename__ = "task_artifacts"
    __table_args__ = ({"schema": "tasks"},)

    id: Mapped[UUID] = _uuid_pk()
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.task_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'inline'"))
    content_inline: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    yjs_document_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    mime_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'text/markdown'")
    )
    byte_size: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    content_hash_sha256: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    created_at: Mapped[datetime] = _ts_default_now()
