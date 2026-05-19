"""Unit: AuthorizationService.has_permission — mock-only.

The implementation issues a single SELECT JOIN; the test asserts that
has_permission returns True iff session.execute().first() returns a row.
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
    result.first.return_value = (uuid4(),) if found else None
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_has_permission_true_when_row_found() -> None:
    session = _session_returning(found=True)
    svc = AuthorizationService(session)
    granted = await svc.has_permission(
        user_id=uuid4(),
        scope_type="cell",
        scope_id=uuid4(),
        permission_slug="cell.view",
    )
    assert granted is True
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_has_permission_false_when_no_rows() -> None:
    session = _session_returning(found=False)
    svc = AuthorizationService(session)
    granted = await svc.has_permission(
        user_id=uuid4(),
        scope_type="workspace",
        scope_id=uuid4(),
        permission_slug="workspace.delete",
    )
    assert granted is False


@pytest.mark.asyncio
async def test_has_permission_accepts_both_scope_types() -> None:
    session_w = _session_returning(found=True)
    session_c = _session_returning(found=True)

    assert await AuthorizationService(session_w).has_permission(
        user_id=uuid4(),
        scope_type="workspace",
        scope_id=uuid4(),
        permission_slug="workspace.view",
    )
    assert await AuthorizationService(session_c).has_permission(
        user_id=uuid4(),
        scope_type="cell",
        scope_id=uuid4(),
        permission_slug="cell.view",
    )
