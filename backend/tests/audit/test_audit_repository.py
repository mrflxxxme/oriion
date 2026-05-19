"""Unit: audit.repositories.audit_repository.

Mocks the AsyncSession surface (.add / .flush / .execute) so we don't
need a live DB connection to cover repo branches. The real INSERT path
is also exercised by ``tests/audit/test_audit_log_append_only.py``
(integration) — these tests focus on the call-shape contract.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.audit.repositories.audit_repository import AuditRepository


def _mock_session_with_scalars(rows: list[object]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    result.scalars = MagicMock(return_value=scalars)
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_insert_adds_row_and_flushes() -> None:
    session = _mock_session_with_scalars([])
    repo = AuditRepository(session)

    actor_id = uuid4()
    row = await repo.insert(
        actor_type="user",
        actor_id=actor_id,
        action="iam.user.registered",
        resource_type="user",
        resource_id=actor_id,
        payload={"email": "x@y.dev"},
        ip="1.2.3.4",
        user_agent="pytest",
    )
    assert row.actor_id == actor_id
    assert row.action == "iam.user.registered"
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_by_actor_executes_select() -> None:
    sentinel = [object(), object()]
    session = _mock_session_with_scalars(sentinel)
    repo = AuditRepository(session)

    rows = await repo.list_by_actor(uuid4(), limit=10)
    assert list(rows) == sentinel
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_by_actor_with_cursor() -> None:
    session = _mock_session_with_scalars([])
    repo = AuditRepository(session)

    cursor = datetime.now(UTC)
    rows = await repo.list_by_actor(uuid4(), limit=5, cursor=cursor)
    assert list(rows) == []
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_by_resource_executes_select() -> None:
    session = _mock_session_with_scalars([object()])
    repo = AuditRepository(session)

    rows = await repo.list_by_resource("user", uuid4())
    assert len(list(rows)) == 1
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_by_resource_with_cursor_filters() -> None:
    session = _mock_session_with_scalars([])
    repo = AuditRepository(session)

    cursor = datetime.now(UTC)
    rows = await repo.list_by_resource("workspace", uuid4(), cursor=cursor)
    assert list(rows) == []
    session.execute.assert_awaited_once()
