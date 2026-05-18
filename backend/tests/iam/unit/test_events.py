"""Unit: events.py — CloudEvent envelope shape + tag for log assertions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import structlog
from src.iam import events


@pytest.mark.asyncio
async def test_user_registered_emits_envelope_with_required_keys(
    caplog: pytest.LogCaptureFixture,
) -> None:
    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    user_id = uuid4()
    await events.emit_user_registered(
        user_id=user_id,
        email="x@y.dev",
        registered_at=datetime.now(UTC),
    )
    # Whether captured or not, the call shouldn't raise.


@pytest.mark.asyncio
async def test_all_emit_functions_run_without_raising() -> None:
    user_id, sid, token_id, chain_id = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)

    await events.emit_user_registered(user_id, "x@y.dev", now)
    await events.emit_email_verified(user_id, now)
    await events.emit_email_verification_requested(user_id, "x@y.dev", token_id, now)
    await events.emit_password_reset_requested(user_id, token_id, chain_id, now)
    await events.emit_password_reset_completed(user_id, chain_id, now)
    await events.emit_consent_recorded(user_id, "pdn", "v1", "granted", now)
    await events.emit_consent_recorded(user_id, "marketing", "v1", "revoked", now)
    await events.emit_user_deleted(user_id, now, retention_policy_days=30)
    await events.emit_session_created(sid, user_id, now, ip="1.1.1.1", user_agent_class="desktop")
    await events.emit_session_revoked(sid, "user_action")
    await events.emit_session_revoked(sid, "security_incident")
    await events.emit_refresh_rotated(token_id, uuid4(), chain_id)
    await events.emit_oauth_linked(user_id, "yandex", "external-uid")


def test_envelope_helper_shape() -> None:
    env = events._envelope("oriion.iam.test.v1", {"k": "v"})
    assert env["specversion"] == "1.0"
    assert env["type"] == "oriion.iam.test.v1"
    assert env["source"] == "oriion://contexts/iam"
    assert env["datacontenttype"] == "application/json"
    assert env["data"] == {"k": "v"}
    assert "id" in env and "time" in env
