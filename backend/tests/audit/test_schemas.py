"""Unit: Pydantic 2.x AuditEventCreate / AuditEventOut round-trip."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.audit.schemas import AuditEventCreate, AuditEventOut


def test_audit_event_create_minimal() -> None:
    """Only actor_type + action are mandatory; everything else defaults."""
    ev = AuditEventCreate(actor_type="system", action="iam.test")
    assert ev.actor_type == "system"
    assert ev.action == "iam.test"
    assert ev.actor_id is None
    assert ev.payload is None


def test_audit_event_create_full() -> None:
    """Round-trip with every field populated."""
    aid = uuid4()
    rid = uuid4()
    cid = uuid4()
    wid = uuid4()
    ev = AuditEventCreate(
        actor_type="user",
        actor_id=aid,
        action="iam.user.registered",
        resource_type="user",
        resource_id=rid,
        cell_id=cid,
        workspace_id=wid,
        payload={"foo": "bar"},
        ip="10.0.0.1",
        user_agent="pytest/1.0",
    )
    dumped = ev.model_dump()
    assert dumped["actor_id"] == aid
    assert dumped["payload"] == {"foo": "bar"}
    assert dumped["ip"] == "10.0.0.1"


def test_audit_event_create_rejects_unknown_actor_type() -> None:
    """Literal['user','agent','system'] is the only allowed set."""
    with pytest.raises(ValidationError):
        AuditEventCreate(actor_type="root", action="iam.test")  # type: ignore[arg-type]


def test_audit_event_create_rejects_extra_fields() -> None:
    """extra='forbid' protects against typos / silent drops."""
    with pytest.raises(ValidationError):
        AuditEventCreate(  # type: ignore[call-arg]
            actor_type="system",
            action="iam.test",
            not_a_field="x",
        )


def test_audit_event_create_action_min_length() -> None:
    """Empty action is invalid (avoids silent no-op rows)."""
    with pytest.raises(ValidationError):
        AuditEventCreate(actor_type="system", action="")


def test_audit_event_out_from_attributes() -> None:
    """AuditEventOut.model_validate accepts a SimpleNamespace-y attr object."""
    from types import SimpleNamespace

    row = SimpleNamespace(
        id=uuid4(),
        ts=datetime.now(UTC),
        actor_type="user",
        actor_id=uuid4(),
        action="iam.user.registered",
        resource_type="user",
        resource_id=uuid4(),
        cell_id=None,
        workspace_id=None,
        payload={"k": "v"},
        ip="10.0.0.1",
        user_agent="pytest",
    )
    out = AuditEventOut.model_validate(row)
    assert out.action == "iam.user.registered"
    assert out.payload == {"k": "v"}
