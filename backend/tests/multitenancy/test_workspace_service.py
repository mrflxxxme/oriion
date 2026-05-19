"""Unit: workspace_service — provision_initial_workspace orchestration.

Mocks repos + emit_cloudevent and asserts the call order + arguments. No
DB touched.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.multitenancy.exceptions import CellProvisioningError
from src.multitenancy.services.workspace_service import (
    WorkspaceProvisionResult,
    _sanitize_slug,
    provision_initial_workspace,
)


def test_sanitize_slug_basic() -> None:
    assert _sanitize_slug("Anna.Karenina") == "anna-karenina"


def test_sanitize_slug_strips_repeats() -> None:
    assert _sanitize_slug("a--b___c") == "a-b-c"


def test_sanitize_slug_empty_fallback() -> None:
    assert _sanitize_slug("$$$") == "workspace"


def test_sanitize_slug_trims_leading_trailing_dashes() -> None:
    assert _sanitize_slug("---abc---") == "abc"


def _fake_session_returning(expected_schema: str) -> AsyncMock:
    """Build an AsyncMock that yields the expected schema name from execute()."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = expected_schema
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_provision_initial_workspace_happy_path() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    cell_id = uuid4()
    expected_schema = f"cell_{str(cell_id).replace('-', '_')}"

    session = _fake_session_returning(expected_schema)

    fake_workspace = SimpleNamespace(
        id=workspace_id, slug="user", display_name="user", plan_tier="free"
    )
    fake_cell = SimpleNamespace(
        id=cell_id,
        workspace_id=workspace_id,
        slug="default",
        created_at=datetime.now(UTC),
        vertical_template_slug=None,
    )

    with (
        patch("src.multitenancy.services.workspace_service.WorkspaceRepository") as mock_wr,
        patch("src.multitenancy.services.workspace_service.CellRepository") as mock_cr,
        patch("src.multitenancy.services.workspace_service.emit_workspace_created") as mock_emit_ws,
        patch("src.multitenancy.services.workspace_service.emit_cell_created") as mock_emit_cell,
    ):
        mock_wr.return_value.find_by_slug_active = AsyncMock(return_value=None)
        mock_wr.return_value.create = AsyncMock(return_value=fake_workspace)
        mock_cr.return_value.create = AsyncMock(return_value=fake_cell)
        mock_cr.return_value.find_by_workspace_slug = AsyncMock(return_value=None)
        mock_emit_ws.return_value = None
        mock_emit_cell.return_value = None

        result = await provision_initial_workspace(
            session=session,
            user_id=user_id,
            email_localpart="user",
        )

    assert isinstance(result, WorkspaceProvisionResult)
    assert result.workspace_id == workspace_id
    assert result.cell_id == cell_id

    # workspace created with the sanitized slug + free plan
    mock_wr.return_value.create.assert_awaited_once()
    create_kwargs = mock_wr.return_value.create.await_args.kwargs
    assert create_kwargs["slug"] == "user"
    assert create_kwargs["plan_tier"] == "free"

    # cell created with slug='default' under the new workspace
    mock_cr.return_value.create.assert_awaited_once()
    cell_kwargs = mock_cr.return_value.create.await_args.kwargs
    assert cell_kwargs["slug"] == "default"
    assert cell_kwargs["workspace_id"] == workspace_id

    # provision_cell_schema invoked
    session.execute.assert_awaited()

    # Both CloudEvents emitted
    mock_emit_ws.assert_awaited_once()
    mock_emit_cell.assert_awaited_once()


@pytest.mark.asyncio
async def test_provision_initial_workspace_idempotent_replay() -> None:
    """Re-invocation with same email_localpart returns existing IDs."""
    user_id = uuid4()
    existing_workspace_id = uuid4()
    existing_cell_id = uuid4()

    session = AsyncMock()

    with (
        patch("src.multitenancy.services.workspace_service.WorkspaceRepository") as mock_wr,
        patch("src.multitenancy.services.workspace_service.CellRepository") as mock_cr,
        patch("src.multitenancy.services.workspace_service.emit_workspace_created") as mock_emit_ws,
        patch("src.multitenancy.services.workspace_service.emit_cell_created") as mock_emit_cell,
    ):
        existing_workspace = SimpleNamespace(id=existing_workspace_id, slug="user")
        existing_cell = SimpleNamespace(id=existing_cell_id)
        mock_wr.return_value.find_by_slug_active = AsyncMock(return_value=existing_workspace)
        mock_cr.return_value.find_by_workspace_slug = AsyncMock(return_value=existing_cell)
        mock_wr.return_value.create = AsyncMock()
        mock_cr.return_value.create = AsyncMock()

        result = await provision_initial_workspace(
            session=session, user_id=user_id, email_localpart="user"
        )

    assert result.workspace_id == existing_workspace_id
    assert result.cell_id == existing_cell_id

    # No new rows created
    mock_wr.return_value.create.assert_not_awaited()
    mock_cr.return_value.create.assert_not_awaited()
    # No events emitted on replay
    mock_emit_ws.assert_not_awaited()
    mock_emit_cell.assert_not_awaited()
    # No SQL provisioning either
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_provision_initial_workspace_provision_cell_schema_mismatch() -> None:
    """A bogus schema name from the SQL function bubbles up as CellProvisioningError."""
    user_id = uuid4()
    workspace_id = uuid4()
    cell_id = uuid4()

    session = _fake_session_returning("cell_BOGUS")

    fake_workspace = SimpleNamespace(id=workspace_id)
    fake_cell = SimpleNamespace(
        id=cell_id,
        workspace_id=workspace_id,
        created_at=datetime.now(UTC),
        vertical_template_slug=None,
    )

    with (
        patch("src.multitenancy.services.workspace_service.WorkspaceRepository") as mock_wr,
        patch("src.multitenancy.services.workspace_service.CellRepository") as mock_cr,
    ):
        mock_wr.return_value.find_by_slug_active = AsyncMock(return_value=None)
        mock_wr.return_value.create = AsyncMock(return_value=fake_workspace)
        mock_cr.return_value.create = AsyncMock(return_value=fake_cell)

        with pytest.raises(CellProvisioningError):
            await provision_initial_workspace(
                session=session, user_id=user_id, email_localpart="user"
            )
