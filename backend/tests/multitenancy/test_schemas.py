"""Unit: multitenancy.schemas — Pydantic round-trip + validation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.multitenancy.schemas import (
    CellCreate,
    CellMemberOut,
    CellOut,
    CellPage,
    InvitationCreate,
    InvitationOut,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspacePage,
)


def test_workspace_create_defaults() -> None:
    wc = WorkspaceCreate(display_name="Acme")
    assert wc.display_name == "Acme"
    assert wc.plan_tier == "free"
    assert wc.slug is None


def test_workspace_create_rejects_invalid_plan() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreate(display_name="Acme", plan_tier="unlimited")  # type: ignore[arg-type]


def test_workspace_create_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreate(display_name="Acme", junk_field=1)  # type: ignore[call-arg]


def test_workspace_out_roundtrip() -> None:
    wid = uuid4()
    now = datetime.now(UTC)
    payload = {
        "id": wid,
        "slug": "acme",
        "display_name": "Acme",
        "billing_email": None,
        "country_code": "RU",
        "timezone": "Europe/Moscow",
        "plan_tier": "free",
        "created_at": now,
        "updated_at": now,
    }
    w = WorkspaceOut.model_validate(payload)
    assert w.id == wid
    dump = w.model_dump()
    assert dump["slug"] == "acme"


def test_workspace_page_roundtrip() -> None:
    page = WorkspacePage(items=[], next_cursor=None)
    assert page.items == []
    assert page.next_cursor is None


def test_cell_create_defaults() -> None:
    cc = CellCreate(slug="default", display_name="Default")
    assert cc.settings == {}
    assert cc.vertical_template_slug is None


def test_cell_out_settings_field() -> None:
    cid, wid = uuid4(), uuid4()
    now = datetime.now(UTC)
    cell = CellOut(
        id=cid,
        workspace_id=wid,
        slug="default",
        display_name="Default",
        vertical_template_slug=None,
        settings={"foo": "bar"},
        created_at=now,
        updated_at=now,
        archived_at=None,
    )
    assert cell.settings == {"foo": "bar"}


def test_cell_page_roundtrip() -> None:
    page = CellPage(items=[], next_cursor=None)
    assert page.next_cursor is None


def test_cell_member_out_roundtrip() -> None:
    payload = {
        "id": uuid4(),
        "cell_id": uuid4(),
        "user_id": uuid4(),
        "role_id": uuid4(),
        "joined_at": datetime.now(UTC),
        "invited_by": None,
        "last_active_at": None,
    }
    m = CellMemberOut.model_validate(payload)
    assert m.invited_by is None


def test_invitation_create_requires_email_and_role() -> None:
    with pytest.raises(ValidationError):
        InvitationCreate(email="not-an-email", role_id=uuid4())  # type: ignore[arg-type]


def test_invitation_out_roundtrip() -> None:
    now = datetime.now(UTC)
    inv = InvitationOut(
        id=uuid4(),
        cell_id=uuid4(),
        email="u@x.dev",
        role_id=uuid4(),
        expires_at=now,
        created_at=now,
    )
    assert inv.email == "u@x.dev"
