"""Unit: cell_service — provision/archive/invite/role-change/remove paths."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.multitenancy.exceptions import (
    CellNotFound,
    CellProvisioningError,
    MemberNotFound,
)
from src.multitenancy.services.cell_service import CellService


def _fake_session_returning(schema_name: str) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = schema_name
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_provision_cell_calls_schema_function_and_emits() -> None:
    workspace_id, cell_id, requester = uuid4(), uuid4(), uuid4()
    expected_schema = f"cell_{str(cell_id).replace('-', '_')}"
    session = _fake_session_returning(expected_schema)

    fake_cell = SimpleNamespace(
        id=cell_id,
        workspace_id=workspace_id,
        slug="alpha",
        display_name="Alpha",
        created_at=datetime.now(UTC),
        vertical_template_slug="wb-seller",
    )

    with (
        patch("src.multitenancy.services.cell_service.CellRepository") as mock_cr,
        patch("src.multitenancy.services.cell_service.CellMemberRepository"),
        patch("src.multitenancy.services.cell_service.emit_cell_created") as mock_emit,
        patch("src.multitenancy.services.cell_service.emit_audit_event") as mock_audit,
    ):
        mock_cr.return_value.create = AsyncMock(return_value=fake_cell)

        service = CellService(session)
        cell = await service.provision_cell(
            workspace_id=workspace_id,
            slug="alpha",
            display_name="Alpha",
            vertical_template_slug="wb-seller",
            requested_by_user_id=requester,
        )

    assert cell.id == cell_id
    session.execute.assert_awaited_once()
    mock_emit.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_provision_cell_schema_mismatch_raises() -> None:
    workspace_id, cell_id, requester = uuid4(), uuid4(), uuid4()
    session = _fake_session_returning("cell_BOGUS")
    fake_cell = SimpleNamespace(
        id=cell_id,
        workspace_id=workspace_id,
        created_at=datetime.now(UTC),
        vertical_template_slug=None,
    )

    with patch("src.multitenancy.services.cell_service.CellRepository") as mock_cr:
        mock_cr.return_value.create = AsyncMock(return_value=fake_cell)

        service = CellService(session)
        with pytest.raises(CellProvisioningError):
            await service.provision_cell(
                workspace_id=workspace_id,
                slug="bad",
                display_name="Bad",
                vertical_template_slug=None,
                requested_by_user_id=requester,
            )


@pytest.mark.asyncio
async def test_archive_cell_not_found_raises() -> None:
    session = AsyncMock()
    with patch("src.multitenancy.services.cell_service.CellRepository") as mock_cr:
        mock_cr.return_value.find_by_id = AsyncMock(return_value=None)
        service = CellService(session)
        with pytest.raises(CellNotFound):
            await service.archive_cell(cell_id=uuid4(), archived_by=uuid4())


@pytest.mark.asyncio
async def test_archive_cell_emits_event_and_audit() -> None:
    session = AsyncMock()
    cell_id = uuid4()
    fake_cell = SimpleNamespace(id=cell_id)
    with (
        patch("src.multitenancy.services.cell_service.CellRepository") as mock_cr,
        patch("src.multitenancy.services.cell_service.emit_cell_archived") as mock_emit,
        patch("src.multitenancy.services.cell_service.emit_audit_event") as mock_audit,
    ):
        mock_cr.return_value.find_by_id = AsyncMock(return_value=fake_cell)
        mock_cr.return_value.archive = AsyncMock(return_value=None)
        service = CellService(session)
        await service.archive_cell(cell_id=cell_id, archived_by=uuid4())
    mock_emit.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_role_member_not_found() -> None:
    session = AsyncMock()
    with patch("src.multitenancy.services.cell_service.CellMemberRepository") as mock_mr:
        mock_mr.return_value.find_by_cell_user = AsyncMock(return_value=None)
        service = CellService(session)
        with pytest.raises(MemberNotFound):
            await service.change_role(
                cell_id=uuid4(),
                user_id=uuid4(),
                new_role_id=uuid4(),
                changed_by=uuid4(),
            )


@pytest.mark.asyncio
async def test_change_role_noop_when_role_unchanged() -> None:
    session = AsyncMock()
    role_id = uuid4()
    existing = SimpleNamespace(role_id=role_id, cell_id=uuid4(), user_id=uuid4())
    with (
        patch("src.multitenancy.services.cell_service.CellMemberRepository") as mock_mr,
        patch("src.multitenancy.services.cell_service.emit_member_role_changed") as mock_emit,
    ):
        mock_mr.return_value.find_by_cell_user = AsyncMock(return_value=existing)
        service = CellService(session)
        member = await service.change_role(
            cell_id=uuid4(),
            user_id=uuid4(),
            new_role_id=role_id,
            changed_by=uuid4(),
        )
    assert member is existing
    mock_emit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_role_updates_and_emits() -> None:
    session = AsyncMock()
    old_role_id, new_role_id = uuid4(), uuid4()
    existing = SimpleNamespace(role_id=old_role_id, cell_id=uuid4(), user_id=uuid4())
    with (
        patch("src.multitenancy.services.cell_service.CellMemberRepository") as mock_mr,
        patch("src.multitenancy.services.cell_service.emit_member_role_changed") as mock_emit,
        patch("src.multitenancy.services.cell_service.emit_audit_event") as mock_audit,
    ):
        mock_mr.return_value.find_by_cell_user = AsyncMock(return_value=existing)
        mock_mr.return_value.update_role = AsyncMock(return_value=None)
        service = CellService(session)
        member = await service.change_role(
            cell_id=uuid4(),
            user_id=uuid4(),
            new_role_id=new_role_id,
            changed_by=uuid4(),
        )
    assert member.role_id == new_role_id
    mock_emit.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_invite_member_not_found_raises() -> None:
    session = AsyncMock()
    with patch("src.multitenancy.services.cell_service.CellRepository") as mock_cr:
        mock_cr.return_value.find_by_id = AsyncMock(return_value=None)
        service = CellService(session)
        with pytest.raises(CellNotFound):
            await service.invite_member(
                cell_id=uuid4(),
                email="x@y.dev",
                role_id=uuid4(),
                invited_by=uuid4(),
            )


@pytest.mark.asyncio
async def test_invite_member_emits_event_and_audit() -> None:
    session = AsyncMock()
    cell_id = uuid4()
    with (
        patch("src.multitenancy.services.cell_service.CellRepository") as mock_cr,
        patch("src.multitenancy.services.cell_service.emit_member_invited") as mock_emit,
        patch("src.multitenancy.services.cell_service.emit_audit_event") as mock_audit,
    ):
        mock_cr.return_value.find_by_id = AsyncMock(return_value=SimpleNamespace(id=cell_id))
        service = CellService(session)
        invitation_id, expires_at = await service.invite_member(
            cell_id=cell_id,
            email="x@y.dev",
            role_id=uuid4(),
            invited_by=uuid4(),
        )
    assert invitation_id is not None
    assert expires_at is not None
    mock_emit.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_member_not_found_raises() -> None:
    session = AsyncMock()
    with patch("src.multitenancy.services.cell_service.CellMemberRepository") as mock_mr:
        mock_mr.return_value.find_by_cell_user = AsyncMock(return_value=None)
        service = CellService(session)
        with pytest.raises(MemberNotFound):
            await service.remove_member(cell_id=uuid4(), user_id=uuid4(), removed_by=uuid4())


@pytest.mark.asyncio
async def test_remove_member_emits_event_and_audit() -> None:
    session = AsyncMock()
    cell_id, user_id = uuid4(), uuid4()
    with (
        patch("src.multitenancy.services.cell_service.CellMemberRepository") as mock_mr,
        patch("src.multitenancy.services.cell_service.emit_member_removed") as mock_emit,
        patch("src.multitenancy.services.cell_service.emit_audit_event") as mock_audit,
    ):
        mock_mr.return_value.find_by_cell_user = AsyncMock(
            return_value=SimpleNamespace(role_id=uuid4())
        )
        mock_mr.return_value.remove = AsyncMock(return_value=None)
        service = CellService(session)
        await service.remove_member(cell_id=cell_id, user_id=user_id, removed_by=uuid4())
    mock_emit.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_creator_as_owner_idempotent() -> None:
    session = AsyncMock()
    existing = SimpleNamespace(id=uuid4())
    with patch("src.multitenancy.services.cell_service.CellMemberRepository") as mock_mr:
        mock_mr.return_value.find_by_cell_user = AsyncMock(return_value=existing)
        mock_mr.return_value.add_member = AsyncMock()
        service = CellService(session)
        result = await service.add_creator_as_owner(
            cell_id=uuid4(), user_id=uuid4(), owner_role_id=uuid4()
        )
    assert result is existing
    mock_mr.return_value.add_member.assert_not_awaited()
