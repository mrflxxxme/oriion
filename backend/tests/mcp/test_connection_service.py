"""Unit: MCPConnectionService — CRUD callable surface.

Tests mock `AsyncSession` rather than wiring a real DB. Integration of
RLS + actual SQL belongs in the alembic + RLS integration suite (Wave 2+
when production MCP servers ship).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.mcp.models import MCPConnection
from src.mcp.schemas import MCPConnectionCreate
from src.mcp.services.connection_service import MCPConnectionService


def _make_session() -> tuple[Any, AsyncMock]:
    """Build a MagicMock AsyncSession with `execute` as AsyncMock."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session, session.execute


@pytest.mark.asyncio
async def test_create_inserts_and_flushes_row() -> None:
    session, _execute = _make_session()
    service = MCPConnectionService(session=session)
    cmd = MCPConnectionCreate(
        workspace_id=uuid4(),
        name="brave-search",
        server_type="http",
        endpoint="https://example.test/mcp",
    )
    row = await service.create(cmd)
    assert isinstance(row, MCPConnection)
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_get_returns_none_when_missing() -> None:
    session, execute = _make_session()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = None
    execute.return_value = scalar_result
    service = MCPConnectionService(session=session)
    result = await service.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_row_when_present() -> None:
    session, execute = _make_session()
    row = MCPConnection(
        workspace_id=uuid4(),
        name="brave-search",
        server_type="http",
        endpoint="https://example.test/mcp",
    )
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = row
    execute.return_value = scalar_result
    service = MCPConnectionService(session=session)
    fetched = await service.get(uuid4())
    assert fetched is row


@pytest.mark.asyncio
async def test_list_by_workspace_filters_only_active_by_default() -> None:
    session, execute = _make_session()
    scalars = MagicMock()
    scalars.all.return_value = []
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars
    execute.return_value = exec_result
    service = MCPConnectionService(session=session)
    rows = await service.list_by_workspace(uuid4())
    assert rows == []
    # Ensure execute was called exactly once with a Select object
    assert execute.await_count == 1


@pytest.mark.asyncio
async def test_deactivate_returns_false_when_no_row_updated() -> None:
    session, execute = _make_session()
    exec_result = MagicMock()
    exec_result.rowcount = 0
    execute.return_value = exec_result
    service = MCPConnectionService(session=session)
    updated = await service.deactivate(uuid4())
    assert updated is False


@pytest.mark.asyncio
async def test_deactivate_returns_true_when_row_updated() -> None:
    session, execute = _make_session()
    exec_result = MagicMock()
    exec_result.rowcount = 1
    execute.return_value = exec_result
    service = MCPConnectionService(session=session)
    updated = await service.deactivate(uuid4())
    assert updated is True
