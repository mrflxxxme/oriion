"""Unit: multitenancy.models — table-name + schema + column shape via inspect.

No DB needed — these tests interrogate SQLAlchemy metadata only.
"""

from __future__ import annotations

from sqlalchemy import inspect
from src.multitenancy.models import Cell, CellMember, Workspace


def test_workspace_tablename_and_schema() -> None:
    assert Workspace.__tablename__ == "workspaces"
    assert Workspace.__table__.schema == "multitenancy"


def test_cell_tablename_and_schema() -> None:
    assert Cell.__tablename__ == "cells"
    assert Cell.__table__.schema == "multitenancy"


def test_cell_member_tablename_and_schema() -> None:
    assert CellMember.__tablename__ == "cell_members"
    assert CellMember.__table__.schema == "multitenancy"


def test_workspace_has_expected_columns() -> None:
    cols = {c.name for c in inspect(Workspace).columns}
    assert {
        "id",
        "slug",
        "display_name",
        "billing_email",
        "country_code",
        "timezone",
        "plan_tier",
        "created_at",
        "updated_at",
        "deleted_at",
    } <= cols


def test_cell_has_expected_columns() -> None:
    cols = {c.name for c in inspect(Cell).columns}
    assert {
        "id",
        "workspace_id",
        "slug",
        "display_name",
        "vertical_template_slug",
        "settings_jsonb",
        "created_at",
        "updated_at",
        "archived_at",
    } <= cols


def test_cell_member_has_expected_columns() -> None:
    cols = {c.name for c in inspect(CellMember).columns}
    assert {
        "id",
        "cell_id",
        "user_id",
        "role_id",
        "joined_at",
        "invited_by",
        "last_active_at",
    } <= cols


def test_cell_workspace_fk_targets_workspaces() -> None:
    fks = list(inspect(Cell).columns["workspace_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "multitenancy.workspaces.id"


def test_cell_member_cell_fk_cascade() -> None:
    fks = list(inspect(CellMember).columns["cell_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "multitenancy.cells.id"
    assert fks[0].ondelete == "CASCADE"
