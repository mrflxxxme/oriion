"""Unit: AuthorizationService.has_cell_permission — mock-only.

The implementation issues a single raw SELECT joining cell_members →
role_permissions → permissions; the test asserts has_cell_permission returns
True iff session.execute().first() returns a row (default-deny otherwise).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.rbac.services.authorization_service import AuthorizationService


def _session_returning(found: bool) -> AsyncMock:
    """AsyncMock session whose execute().first() returns a tuple or None."""
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = (1,) if found else None
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_owner_row_found_grants() -> None:
    session = _session_returning(found=True)
    svc = AuthorizationService(session)
    granted = await svc.has_cell_permission(
        user_id=uuid4(),
        cell_id=uuid4(),
        permission_slug="member.invite",
    )
    assert granted is True
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_row_denies() -> None:
    session = _session_returning(found=False)
    svc = AuthorizationService(session)
    granted = await svc.has_cell_permission(
        user_id=uuid4(),
        cell_id=uuid4(),
        permission_slug="billing.manage",
    )
    assert granted is False


@pytest.mark.asyncio
async def test_query_is_parameterised() -> None:
    """The user/cell/slug values are passed as bound params, never interpolated."""
    session = _session_returning(found=True)
    svc = AuthorizationService(session)
    user_id, cell_id = uuid4(), uuid4()
    await svc.has_cell_permission(
        user_id=user_id,
        cell_id=cell_id,
        permission_slug="cell.archive",
    )
    _, kwargs = session.execute.call_args
    # execute(stmt, params) — params is the 2nd positional arg.
    params = session.execute.call_args.args[1]
    assert params == {
        "cell_id": str(cell_id),
        "user_id": str(user_id),
        "slug": "cell.archive",
    }
