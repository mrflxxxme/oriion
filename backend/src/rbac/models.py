"""SQLAlchemy 2.x models for rbac bounded context.

Schema authoritative per .planning/contracts/rbac/schema.sql (ADR-024).
Tables live under PostgreSQL schema `rbac`. Migrations:
  backend/migrations/versions/rbac/0001..0005_*.py
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    text,
)
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


class SystemRole(Base):
    """Built-in role catalogue. slug is the stable identifier."""

    __tablename__ = "system_roles"
    __table_args__ = (
        Index("system_roles_slug_uidx", "slug", unique=True),
        {"schema": "rbac"},
    )

    id: Mapped[UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_built_in: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()


class Permission(Base):
    """Granular permission catalogue. slug format `<resource>.<action>`."""

    __tablename__ = "permissions"
    __table_args__ = (
        CheckConstraint(
            r"slug ~ '^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$'",
            name="permissions_slug_format_check",
        ),
        Index("permissions_slug_uidx", "slug", unique=True),
        Index("permissions_category_idx", "category"),
        {"schema": "rbac"},
    )

    id: Mapped[UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts_default_now()


class RolePermission(Base):
    """Many-to-many bridge between SystemRole and Permission."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        PrimaryKeyConstraint("role_id", "permission_id"),
        Index("role_permissions_permission_id_idx", "permission_id"),
        {"schema": "rbac"},
    )

    role_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rbac.system_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rbac.permissions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = _ts_default_now()

    role: Mapped[SystemRole] = relationship()
    permission: Mapped[Permission] = relationship()


class RoleAssignment(Base):
    """(user, scope_type, scope_id, role) binding with optional expires_at.

    Cross-context FKs (iam.users.id, multitenancy.workspaces.id / cells.id)
    are NOT enforced at the DB layer — see ADR-024 Consequences.
    """

    __tablename__ = "role_assignments"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('workspace','cell')",
            name="role_assignments_scope_type_check",
        ),
        Index(
            "role_assignments_unique_uidx",
            "user_id",
            "scope_type",
            "scope_id",
            "role_id",
            unique=True,
        ),
        Index("role_assignments_user_idx", "user_id"),
        Index("role_assignments_scope_idx", "scope_type", "scope_id"),
        Index(
            "role_assignments_expiring_idx",
            "expires_at",
            postgresql_where=text("expires_at IS NOT NULL"),
        ),
        {"schema": "rbac"},
    )

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    role_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rbac.system_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    assigned_at: Mapped[datetime] = _ts_default_now()
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    role: Mapped[SystemRole] = relationship()
