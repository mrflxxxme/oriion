"""Unit: multitenancy.events — assert ce_type + structlog tag on emit.

structlog.testing.capture_logs() reliably intercepts because emit_cloudevent
resolves the logger inside the function body (no module-level caching) — the
lazy proxy re-evaluates through the current config on every call.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import structlog
from src.multitenancy import events


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    """Reset structlog defaults before each test for cross-test independence."""
    structlog.reset_defaults()


@pytest.mark.asyncio
async def test_emit_workspace_created_includes_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_workspace_created(
            workspace_id=uuid4(),
            slug="acme",
            plan_tier="free",
            created_by_user_id=uuid4(),
        )
    assert len(logs) == 1
    assert logs[0]["ce_type"] == "oriion.multitenancy.workspace.created.v1"
    assert logs[0]["cloudevent"] is True
    assert logs[0]["data"]["slug"] == "acme"


@pytest.mark.asyncio
async def test_emit_workspace_plan_changed_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_workspace_plan_changed(
            workspace_id=uuid4(),
            old_plan="free",
            new_plan="starter",
            changed_at=datetime.now(UTC),
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.workspace.plan_changed.v1"


@pytest.mark.asyncio
async def test_emit_cell_created_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_cell_created(
            cell_id=uuid4(),
            workspace_id=uuid4(),
            created_at=datetime.now(UTC),
            vertical_template_slug="wb-seller",
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.cell.created.v1"
    assert logs[0]["data"]["vertical_template_slug"] == "wb-seller"


@pytest.mark.asyncio
async def test_emit_cell_archived_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_cell_archived(
            cell_id=uuid4(),
            archived_by=uuid4(),
            archived_at=datetime.now(UTC),
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.cell.archived.v1"


@pytest.mark.asyncio
async def test_emit_member_invited_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_member_invited(
            invitation_id=uuid4(),
            cell_id=uuid4(),
            email="x@y.dev",
            role_id=uuid4(),
            invited_by=uuid4(),
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.member.invited.v1"
    assert logs[0]["data"]["email"] == "x@y.dev"


@pytest.mark.asyncio
async def test_emit_member_joined_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_member_joined(
            cell_id=uuid4(),
            user_id=uuid4(),
            role_id=uuid4(),
            joined_at=datetime.now(UTC),
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.member.joined.v1"


@pytest.mark.asyncio
async def test_emit_member_role_changed_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_member_role_changed(
            cell_id=uuid4(),
            user_id=uuid4(),
            old_role_id=uuid4(),
            new_role_id=uuid4(),
            changed_by=uuid4(),
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.member.role_changed.v1"


@pytest.mark.asyncio
async def test_emit_member_removed_ce_type() -> None:
    with structlog.testing.capture_logs() as logs:
        await events.emit_member_removed(
            cell_id=uuid4(),
            user_id=uuid4(),
            removed_by=uuid4(),
            removed_at=datetime.now(UTC),
        )
    assert logs[0]["ce_type"] == "oriion.multitenancy.member.removed.v1"
