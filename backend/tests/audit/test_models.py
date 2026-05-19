"""Unit: AuditLog SQLAlchemy model — schema, PK, columns."""

from __future__ import annotations

from src.audit.models import AuditLog


def test_audit_log_lives_in_audit_schema() -> None:
    """Table must be in the 'audit' schema (matches migration DDL)."""
    assert AuditLog.__table__.schema == "audit"
    assert AuditLog.__tablename__ == "audit_log"


def test_audit_log_composite_primary_key_is_id_ts() -> None:
    """PK is composite (id, ts) because ts is the partition key.

    Postgres requires every partition-key column to participate in every
    UNIQUE / PK constraint, so the logical-id-only PK is impossible here.
    """
    pk_columns = [c.name for c in AuditLog.__table__.primary_key.columns]
    assert set(pk_columns) == {"id", "ts"}


def test_audit_log_has_all_required_columns() -> None:
    """Column set matches the migration DDL exactly."""
    expected = {
        "id",
        "ts",
        "actor_type",
        "actor_id",
        "action",
        "resource_type",
        "resource_id",
        "cell_id",
        "workspace_id",
        "payload",
        "ip",
        "user_agent",
    }
    actual = {c.name for c in AuditLog.__table__.columns}
    assert actual == expected


def test_audit_log_actor_type_check_constraint_present() -> None:
    """CHECK constraint on actor_type must be declared on the model."""
    from sqlalchemy import CheckConstraint

    constraints = [c for c in AuditLog.__table__.constraints if isinstance(c, CheckConstraint)]
    assert any(
        "actor_type" in str(c.sqltext) and "user" in str(c.sqltext) for c in constraints
    ), "Expected actor_type IN ('user','agent','system') CHECK"


def test_audit_log_nullable_columns() -> None:
    """actor_id / resource_type / resource_id / cell_id / workspace_id /
    payload / ip / user_agent are all nullable; the rest are NOT NULL."""
    cols = {c.name: c for c in AuditLog.__table__.columns}
    nullable = {
        "actor_id",
        "resource_type",
        "resource_id",
        "cell_id",
        "workspace_id",
        "payload",
        "ip",
        "user_agent",
    }
    for name in nullable:
        assert cols[name].nullable, f"{name} should be nullable"
    for name in ("id", "ts", "actor_type", "action"):
        assert not cols[name].nullable, f"{name} should be NOT NULL"
