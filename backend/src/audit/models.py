"""SQLAlchemy 2.x models for audit bounded context.

Schema is authoritative per .planning/roadmap/wave-0-foundation/phases/
00.3-db-rls-multitenancy.md (Audit log partitioning section) and ADR-014
amendment 2026-05-19 (append-only enforcement, 3-year retention).

Tables live under PostgreSQL schema ``audit``. Migration:
  backend/migrations/versions/audit/0001_audit_log_partitioned.py

Important: ``audit.audit_log`` is RANGE-partitioned by ``ts``. Postgres
requires every column of the partition key to be part of every UNIQUE/PK
constraint, so the primary key is the *composite* ``(id, ts)`` even though
the application treats ``id`` as the logical identifier.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base


class AuditLog(Base):
    """Append-only audit log row.

    Inserts only — UPDATE and DELETE are rejected by the
    ``audit.deny_update_delete()`` trigger (see migration). The trigger is
    the *authoritative* enforcement; the missing UPDATE/DELETE grants in
    the migration are a belt-and-braces second line.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        # Composite PK because ts is the partition key (PG requirement).
        PrimaryKeyConstraint("id", "ts", name="audit_log_pkey"),
        CheckConstraint(
            "actor_type IN ('user','agent','system')",
            name="audit_log_actor_type_check",
        ),
        Index("audit_log_ts_idx", text("ts DESC")),
        Index(
            "audit_log_actor_id_ts_idx",
            "actor_id",
            text("ts DESC"),
            postgresql_where=text("actor_id IS NOT NULL"),
        ),
        Index("audit_log_action_ts_idx", "action", text("ts DESC")),
        Index(
            "audit_log_cell_id_ts_idx",
            "cell_id",
            text("ts DESC"),
            postgresql_where=text("cell_id IS NOT NULL"),
        ),
        Index(
            "audit_log_workspace_id_ts_idx",
            "workspace_id",
            text("ts DESC"),
            postgresql_where=text("workspace_id IS NOT NULL"),
        ),
        {"schema": "audit"},
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(
        server_default=text("now()"),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    cell_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    workspace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
