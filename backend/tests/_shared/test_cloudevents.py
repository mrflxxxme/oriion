"""Unit tests for src._shared.cloudevents.emit_cloudevent.

These tests do NOT touch Postgres — they assert the CloudEvents 1.0 envelope
fields on the emitted structlog record. Wave 1+ swap to Redis Streams will
update these tests to assert against the new transport.
"""

from __future__ import annotations

import pytest
import structlog
from src._shared.cloudevents import emit_cloudevent


@pytest.mark.asyncio
async def test_emit_cloudevent_includes_specversion_and_type() -> None:
    """Assert ce_specversion='1.0' and ce_type land on the log record."""
    with structlog.testing.capture_logs() as logs:
        await emit_cloudevent(
            ce_type="oriion.multitenancy.workspace.created.v1",
            source="oriion://contexts/multitenancy",
            data={"workspace_id": "00000000-0000-0000-0000-000000000001"},
        )
    assert len(logs) == 1
    record = logs[0]
    assert record["cloudevent"] is True
    assert record["ce_specversion"] == "1.0"
    assert record["ce_type"] == "oriion.multitenancy.workspace.created.v1"
    assert record["ce_source"] == "oriion://contexts/multitenancy"
    assert record["data"] == {"workspace_id": "00000000-0000-0000-0000-000000000001"}
    assert record["event"] == "cloudevent.emitted"


@pytest.mark.asyncio
async def test_emit_cloudevent_uses_provided_correlation_id() -> None:
    """Caller-provided correlation_id survives onto the record."""
    correlation = "trace-abc-123"
    with structlog.testing.capture_logs() as logs:
        await emit_cloudevent(
            ce_type="oriion.llm-gateway.request.completed.v1",
            source="oriion://contexts/llm-gateway",
            data={"request_id": "req-1"},
            correlation_id=correlation,
        )
    assert logs[0]["ce_correlation_id"] == correlation


@pytest.mark.asyncio
async def test_emit_cloudevent_generates_fresh_id_each_call() -> None:
    """Each emit gets a unique ce_id (uuid4)."""
    with structlog.testing.capture_logs() as logs:
        await emit_cloudevent(
            ce_type="oriion.audit.event.recorded.v1",
            source="oriion://contexts/audit",
            data={"action": "test"},
        )
        await emit_cloudevent(
            ce_type="oriion.audit.event.recorded.v1",
            source="oriion://contexts/audit",
            data={"action": "test"},
        )
    assert logs[0]["ce_id"] != logs[1]["ce_id"]
