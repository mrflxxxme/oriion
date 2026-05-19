"""Unit: AuditService + module-level emit_audit_event.

Verifies the two behaviour modes of ``emit_audit_event``:
  1. session=None → structlog-only fallback (Phase 00.2 stub parity)
  2. session=AsyncSession → INSERT via AuditRepository (Phase 00.3 real impl)

A CloudEvent is emitted in BOTH modes — that's the observability contract.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import structlog
from src.audit.repositories.audit_repository import AuditRepository
from src.audit.services.audit_service import AuditService, emit_audit_event


@pytest.mark.asyncio
async def test_emit_audit_event_without_session_logs_structlog_record() -> None:
    """No session → no DB write; structlog record is the sole sink."""
    with structlog.testing.capture_logs() as logs:
        await emit_audit_event(
            actor_type="user",
            actor_id=uuid4(),
            action="iam.user.registered",
            resource_type="user",
            resource_id=uuid4(),
            payload={"foo": "bar"},
            ip="10.0.0.1",
            user_agent="pytest",
        )

    audit_records = [r for r in logs if r.get("audit_event") is True]
    assert len(audit_records) == 1, "expected exactly one audit_event log record"
    assert audit_records[0]["action"] == "iam.user.registered"
    assert audit_records[0]["actor_type"] == "user"


@pytest.mark.asyncio
async def test_emit_audit_event_without_session_emits_cloudevent() -> None:
    """CloudEvent is emitted on every call regardless of session presence."""
    with structlog.testing.capture_logs() as logs:
        await emit_audit_event(
            actor_type="system",
            actor_id=uuid4(),
            action="iam.session.created",
        )

    cloudevents = [r for r in logs if r.get("cloudevent") is True]
    assert len(cloudevents) == 1
    assert cloudevents[0]["ce_type"] == "oriion.audit.event.recorded.v1"
    assert cloudevents[0]["ce_source"] == "oriion://contexts/audit"
    assert cloudevents[0]["data"]["action"] == "iam.session.created"


@pytest.mark.asyncio
async def test_emit_audit_event_with_session_inserts_via_repo() -> None:
    """When session is provided, AuditRepository.insert is called once
    with the propagated args; structlog fallback is NOT used."""
    session = AsyncMock()
    actor_id = uuid4()
    resource_id = uuid4()
    workspace_id = uuid4()
    cell_id = uuid4()

    with (
        patch.object(AuditRepository, "insert", new_callable=AsyncMock) as insert_mock,
        structlog.testing.capture_logs() as logs,
    ):
        await emit_audit_event(
            actor_type="user",
            actor_id=actor_id,
            action="iam.user.registered",
            resource_type="user",
            resource_id=resource_id,
            payload={"k": "v"},
            ip="10.0.0.2",
            user_agent="pytest",
            session=session,
            workspace_id=workspace_id,
            cell_id=cell_id,
        )

    insert_mock.assert_awaited_once()
    kwargs = insert_mock.await_args.kwargs
    assert kwargs["actor_type"] == "user"
    assert kwargs["actor_id"] == actor_id
    assert kwargs["action"] == "iam.user.registered"
    assert kwargs["resource_id"] == resource_id
    assert kwargs["cell_id"] == cell_id
    assert kwargs["workspace_id"] == workspace_id

    # No stub-fallback structlog record in DB-path mode.
    assert not [r for r in logs if r.get("audit_event") is True]

    # CloudEvent still emitted (observability contract).
    cloudevents = [r for r in logs if r.get("cloudevent") is True]
    assert len(cloudevents) == 1


@pytest.mark.asyncio
async def test_emit_audit_event_cloudevent_carries_full_discriminator() -> None:
    """The single canonical ce_type relies on data.action for discrimination."""
    actor_id = uuid4()
    with structlog.testing.capture_logs() as logs:
        await emit_audit_event(
            actor_type="agent",
            actor_id=actor_id,
            action="agent.tool.invoked",
            resource_type="tool",
            payload={"tool_name": "search"},
        )
    ce = next(r for r in logs if r.get("cloudevent") is True)
    assert ce["data"]["action"] == "agent.tool.invoked"
    assert ce["data"]["actor_type"] == "agent"
    assert ce["data"]["actor_id"] == str(actor_id)
    assert ce["data"]["payload"] == {"tool_name": "search"}
    assert ce["ce_subject"] == "agent.tool.invoked"


@pytest.mark.asyncio
async def test_audit_service_record_delegates_to_repo() -> None:
    """AuditService.record forwards every kwarg to AuditRepository.insert."""
    repo = AsyncMock(spec=AuditRepository)
    svc = AuditService(repo)
    actor_id = uuid4()

    with structlog.testing.capture_logs() as logs:
        await svc.record(
            actor_type="system",
            actor_id=actor_id,
            action="iam.test",
            payload={"a": 1},
        )

    repo.insert.assert_awaited_once_with(
        actor_type="system",
        actor_id=actor_id,
        action="iam.test",
        resource_type=None,
        resource_id=None,
        cell_id=None,
        workspace_id=None,
        payload={"a": 1},
        ip=None,
        user_agent=None,
    )
    # CloudEvent observability still fires.
    assert [r for r in logs if r.get("cloudevent") is True]


@pytest.mark.asyncio
async def test_emit_audit_event_stub_compat_call_works() -> None:
    """Exact stub call shape (positional, no session) still type-checks
    and executes without error — the import-swap guarantee."""
    await emit_audit_event(
        "user",
        uuid4(),
        "iam.user.registered",
        "user",
        uuid4(),
        {"foo": "bar"},
        "1.2.3.4",
        "pytest",
    )
