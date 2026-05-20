"""Unit: workspace_service — provision_initial_workspace orchestration.

Mocks session.execute + emit_cloudevent and asserts the call shape +
arguments to the new SECURITY DEFINER `multitenancy.bootstrap_first_workspace`
SQL function (introduced in migration
``multitenancy/0005_bootstrap_first_workspace_function.py`` per Phase 00.5
Topic 1, RLS Option A, 2026-05-20). No DB touched.
"""

from __future__ import annotations

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


def _fake_session_returning(row: tuple[str, str, str, bool] | None) -> AsyncMock:
    """Build an AsyncMock whose execute() result.first() returns the given row.

    Row tuple shape matches the SQL function output:
        (workspace_id::text, cell_id::text, schema_name, was_replay)
    """
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = row
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_provision_initial_workspace_happy_path() -> None:
    """Fresh-create path: bootstrap function returns was_replay=False,
    both CloudEvents emitted, WorkspaceProvisionResult populated.
    """
    user_id = uuid4()
    workspace_id = uuid4()
    cell_id = uuid4()
    expected_schema = f"cell_{str(cell_id).replace('-', '_')}"

    session = _fake_session_returning((str(workspace_id), str(cell_id), expected_schema, False))

    with (
        patch("src.multitenancy.services.workspace_service.emit_workspace_created") as mock_emit_ws,
        patch("src.multitenancy.services.workspace_service.emit_cell_created") as mock_emit_cell,
    ):
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

    # SQL function called once with sanitized slug + email_localpart
    session.execute.assert_awaited_once()
    call_args = session.execute.await_args
    statement = str(call_args.args[0])
    params = call_args.args[1]
    assert "multitenancy.bootstrap_first_workspace" in statement
    assert params["user_id"] == str(user_id)
    assert params["slug"] == "user"
    assert params["display_name"] == "user"

    # Both CloudEvents emitted with correct workspace_id + cell_id
    mock_emit_ws.assert_awaited_once()
    ws_kwargs = mock_emit_ws.await_args.kwargs
    assert ws_kwargs["workspace_id"] == workspace_id
    assert ws_kwargs["slug"] == "user"
    assert ws_kwargs["plan_tier"] == "free"
    assert ws_kwargs["created_by_user_id"] == user_id

    mock_emit_cell.assert_awaited_once()
    cell_kwargs = mock_emit_cell.await_args.kwargs
    assert cell_kwargs["cell_id"] == cell_id
    assert cell_kwargs["workspace_id"] == workspace_id
    # Wave-0 productivity-core: vertical_template_slug is always None
    assert cell_kwargs["vertical_template_slug"] is None


@pytest.mark.asyncio
async def test_provision_initial_workspace_idempotent_replay() -> None:
    """Replay path: bootstrap function returns was_replay=True with existing
    IDs; NO CloudEvents emitted (already fired on first registration).
    """
    user_id = uuid4()
    existing_workspace_id = uuid4()
    existing_cell_id = uuid4()
    expected_schema = f"cell_{str(existing_cell_id).replace('-', '_')}"

    session = _fake_session_returning(
        (str(existing_workspace_id), str(existing_cell_id), expected_schema, True)
    )

    with (
        patch("src.multitenancy.services.workspace_service.emit_workspace_created") as mock_emit_ws,
        patch("src.multitenancy.services.workspace_service.emit_cell_created") as mock_emit_cell,
    ):
        result = await provision_initial_workspace(
            session=session, user_id=user_id, email_localpart="user"
        )

    assert result.workspace_id == existing_workspace_id
    assert result.cell_id == existing_cell_id

    # SQL function called once (idempotency lives inside the function itself)
    session.execute.assert_awaited_once()

    # No CloudEvents on replay
    mock_emit_ws.assert_not_awaited()
    mock_emit_cell.assert_not_awaited()


@pytest.mark.asyncio
async def test_provision_initial_workspace_schema_mismatch_raises() -> None:
    """SQL function returns mismatched schema_name → CellProvisioningError."""
    user_id = uuid4()
    workspace_id = uuid4()
    cell_id = uuid4()
    bogus_schema = "cell_BOGUS"

    session = _fake_session_returning((str(workspace_id), str(cell_id), bogus_schema, False))

    with pytest.raises(CellProvisioningError, match="returned schema"):
        await provision_initial_workspace(session=session, user_id=user_id, email_localpart="user")


@pytest.mark.asyncio
async def test_provision_initial_workspace_no_row_raises() -> None:
    """SQL function returns None (RETURNING no row) → CellProvisioningError.

    Defensive check — bootstrap_first_workspace always returns exactly one
    row per contract, but the application surface treats the absence as a
    500-class operator-investigates error.
    """
    user_id = uuid4()
    session = _fake_session_returning(None)

    with pytest.raises(CellProvisioningError, match="returned no row"):
        await provision_initial_workspace(session=session, user_id=user_id, email_localpart="user")
