"""Unit: rbac.permissions — slug constants + role grants.

Asserts:
  * All 15 expected permission constants are defined.
  * Each slug matches the CHECK regex from contracts/rbac/schema.sql.
  * BUILT_IN_ROLES contains exactly the 6 expected entries.
  * ROLE_PERMISSIONS matrix matches the seed migration grant rules.
"""

from __future__ import annotations

import re

from src.rbac import permissions
from src.rbac.permissions import (
    ALL_PERMISSIONS,
    BUILT_IN_ROLES,
    ROLE_PERMISSIONS,
)

# Same regex as the CHECK constraint on rbac.permissions.slug.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


EXPECTED_PERMISSION_SLUGS = {
    "workspace.view",
    "workspace.update",
    "workspace.delete",
    "cell.create",
    "cell.view",
    "cell.update",
    "cell.archive",
    "member.invite",
    "member.remove",
    "member.role_change",
    "billing.view",
    "billing.manage",
    "agent.run",
    "task.create",
    "task.view",
}


def test_fifteen_permissions_defined() -> None:
    assert len(ALL_PERMISSIONS) == 15
    assert set(ALL_PERMISSIONS) == EXPECTED_PERMISSION_SLUGS


def test_each_slug_matches_regex() -> None:
    for slug in ALL_PERMISSIONS:
        assert _SLUG_RE.match(slug), f"slug {slug!r} fails contract regex"


def test_six_built_in_roles() -> None:
    assert set(BUILT_IN_ROLES.keys()) == {
        "owner",
        "admin",
        "editor",
        "viewer",
        "billing",
        "guest",
    }


def test_owner_has_all_permissions() -> None:
    assert set(ROLE_PERMISSIONS["owner"]) == EXPECTED_PERMISSION_SLUGS


def test_admin_grants_match_migration() -> None:
    assert set(ROLE_PERMISSIONS["admin"]) == {
        "cell.create",
        "cell.view",
        "cell.update",
        "cell.archive",
        "member.invite",
        "member.remove",
        "member.role_change",
        "agent.run",
        "task.create",
        "task.view",
    }


def test_editor_grants() -> None:
    assert set(ROLE_PERMISSIONS["editor"]) == {
        "cell.view",
        "agent.run",
        "task.create",
        "task.view",
    }


def test_viewer_grants() -> None:
    assert set(ROLE_PERMISSIONS["viewer"]) == {"cell.view", "task.view"}


def test_billing_grants() -> None:
    assert set(ROLE_PERMISSIONS["billing"]) == {
        "billing.view",
        "billing.manage",
        "workspace.view",
    }


def test_guest_grants() -> None:
    assert set(ROLE_PERMISSIONS["guest"]) == {"task.view"}


def test_individual_constants_exposed() -> None:
    """The module exports each permission as a top-level Final[str]."""
    assert permissions.WORKSPACE_VIEW == "workspace.view"
    assert permissions.CELL_CREATE == "cell.create"
    assert permissions.MEMBER_INVITE == "member.invite"
    assert permissions.BILLING_MANAGE == "billing.manage"
    assert permissions.AGENT_RUN == "agent.run"
    assert permissions.TASK_VIEW == "task.view"
