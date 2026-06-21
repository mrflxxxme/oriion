"""SQLAlchemy 2.x models for agents bounded context.

Schema authoritative per .planning/contracts/agents/schema.sql (ADR-024 §2).
Tables live under PostgreSQL schema `agents`. Migrations:
  backend/migrations/versions/agents/0001..0003_*.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base


def _uuid_pk() -> Mapped[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _ts_default_now() -> Mapped[datetime]:
    return mapped_column(server_default=text("now()"), nullable=False)


class AgentArchetype(Base):
    """Vertical-level AI persona. Canonical table per ADR-024 §2."""

    __tablename__ = "agent_archetypes"
    __table_args__ = (
        CheckConstraint(
            "role_category IN ('coordinator','researcher','writer','analyzer',"
            "'validator','communicator','master')",
            name="agent_archetypes_role_category_chk",
        ),
        CheckConstraint(
            "status IN ('draft','reviewed','promoted','locked')",
            name="agent_archetypes_status_chk",
        ),
        UniqueConstraint("vertical_slug", "slug", "prompt_version", name="agent_archetypes_unique"),
        {"schema": "agents"},
    )

    id: Mapped[UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    vertical_slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role_category: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider_slug: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_fallback: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_allowed: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
    deprecated_at: Mapped[datetime | None] = mapped_column(nullable=True)


class TeamPreset(Base):
    """Opinionated archetype composition. Horizontal `productivity-core` is
    seeded by `src.agents.seed_data.productivity_core_v1`."""

    __tablename__ = "team_presets"
    __table_args__ = (
        UniqueConstraint("vertical_slug", "slug", name="team_presets_unique"),
        {"schema": "agents"},
    )

    id: Mapped[UUID] = _uuid_pk()
    vertical_slug: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    archetype_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), nullable=False)
    default_workflow_dag_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()


class AgentInstance(Base):
    """Per-cell instantiation of an archetype. RLS-scoped via current_cell_id."""

    __tablename__ = "agent_instances"
    __table_args__ = (
        Index(
            "idx_agent_instances_cell_active",
            "cell_id",
            postgresql_where=text("archived_at IS NULL"),
        ),
        Index("idx_agent_instances_archetype", "agent_archetype_id"),
        {"schema": "agents"},
    )

    id: Mapped[UUID] = _uuid_pk()
    cell_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("multitenancy.cells.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_archetype_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.agent_archetypes.id"),
        nullable=False,
    )
    custom_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_settings_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    total_tasks_completed: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)
