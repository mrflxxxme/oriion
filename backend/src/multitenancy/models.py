"""SQLAlchemy 2.x models for multitenancy bounded context.

Schema is authoritative per .planning/contracts/multitenancy/schema.sql
(ADR-024). Tables live under PostgreSQL schema `multitenancy`. Migrations:
  backend/migrations/versions/multitenancy/0001..0004_*.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src._shared.db.base import Base


def _uuid_pk() -> Mapped[UUID]:
    """uuid primary key with DB-side gen_random_uuid() default."""
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _ts_default_now() -> Mapped[datetime]:
    return mapped_column(server_default=text("now()"), nullable=False)


class Workspace(Base):
    """Billing / legal tenant (was `organizations` pre-2026-05-19)."""

    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            "plan_tier IN ('free','starter','pro','enterprise')",
            name="workspaces_plan_tier_check",
        ),
        Index(
            "workspaces_slug_active_uidx",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "workspaces_plan_tier_idx",
            "plan_tier",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": "multitenancy"},
    )

    id: Mapped[UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    billing_email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'RU'"))
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Europe/Moscow'")
    )
    plan_tier: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'free'"))
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    cells: Mapped[list[Cell]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class Cell(Base):
    """Workspace boundary = AI team per ADR-009."""

    __tablename__ = "cells"
    __table_args__ = (
        Index(
            "cells_workspace_slug_uidx",
            "workspace_id",
            "slug",
            unique=True,
        ),
        Index(
            "cells_workspace_id_idx",
            "workspace_id",
            postgresql_where=text("archived_at IS NULL"),
        ),
        Index(
            "cells_vertical_template_idx",
            "vertical_template_slug",
            postgresql_where=text("archived_at IS NULL AND vertical_template_slug IS NOT NULL"),
        ),
        {"schema": "multitenancy"},
    )

    id: Mapped[UUID] = _uuid_pk()
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("multitenancy.workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    vertical_template_slug: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)

    workspace: Mapped[Workspace] = relationship(back_populates="cells")
    members: Mapped[list[CellMember]] = relationship(
        back_populates="cell", cascade="all, delete-orphan"
    )


class CellMember(Base):
    """User membership in a cell with a system role.

    Cross-context FKs (iam.users.id, rbac.system_roles.id) are NOT enforced
    at the DB layer — see contract README invariant + ADR-024.
    """

    __tablename__ = "cell_members"
    __table_args__ = (
        Index(
            "cell_members_cell_user_uidx",
            "cell_id",
            "user_id",
            unique=True,
        ),
        Index("cell_members_user_id_idx", "user_id"),
        Index("cell_members_role_id_idx", "role_id"),
        {"schema": "multitenancy"},
    )

    id: Mapped[UUID] = _uuid_pk()
    cell_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("multitenancy.cells.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    role_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    joined_at: Mapped[datetime] = _ts_default_now()
    invited_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(nullable=True)

    cell: Mapped[Cell] = relationship(back_populates="members")
