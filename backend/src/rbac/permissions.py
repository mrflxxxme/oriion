"""Permission slug constants + built-in role catalogue.

Mirrors the seed migration `rbac/0005_seed_built_in_roles.py` 1:1 so
application code can reference permissions by Python identifier rather
than by stringly-typed slug. Any new permission/role MUST be added in
BOTH places + the contracts/rbac/schema.sql seed block (ADR + migration).

The slug-format invariant from rbac.permissions CHECK constraint is
``^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$``. The constants below all conform.
"""

from __future__ import annotations

from typing import Final

# ── 15 core permissions ─────────────────────────────────────────────────

WORKSPACE_VIEW: Final[str] = "workspace.view"
WORKSPACE_UPDATE: Final[str] = "workspace.update"
WORKSPACE_DELETE: Final[str] = "workspace.delete"

CELL_CREATE: Final[str] = "cell.create"
CELL_VIEW: Final[str] = "cell.view"
CELL_UPDATE: Final[str] = "cell.update"
CELL_ARCHIVE: Final[str] = "cell.archive"

MEMBER_INVITE: Final[str] = "member.invite"
MEMBER_REMOVE: Final[str] = "member.remove"
MEMBER_ROLE_CHANGE: Final[str] = "member.role_change"

BILLING_VIEW: Final[str] = "billing.view"
BILLING_MANAGE: Final[str] = "billing.manage"

AGENT_RUN: Final[str] = "agent.run"
TASK_CREATE: Final[str] = "task.create"
TASK_VIEW: Final[str] = "task.view"


ALL_PERMISSIONS: Final[tuple[str, ...]] = (
    WORKSPACE_VIEW,
    WORKSPACE_UPDATE,
    WORKSPACE_DELETE,
    CELL_CREATE,
    CELL_VIEW,
    CELL_UPDATE,
    CELL_ARCHIVE,
    MEMBER_INVITE,
    MEMBER_REMOVE,
    MEMBER_ROLE_CHANGE,
    BILLING_VIEW,
    BILLING_MANAGE,
    AGENT_RUN,
    TASK_CREATE,
    TASK_VIEW,
)


# ── 6 built-in roles ────────────────────────────────────────────────────

BUILT_IN_ROLES: Final[dict[str, str]] = {
    "owner": "Owner",
    "admin": "Admin",
    "editor": "Editor",
    "viewer": "Viewer",
    "billing": "Billing",
    "guest": "Guest",
}


# ── role → permission grants (mirrors the seed migration) ───────────────

ROLE_PERMISSIONS: Final[dict[str, tuple[str, ...]]] = {
    "owner": ALL_PERMISSIONS,
    "admin": (
        CELL_CREATE,
        CELL_VIEW,
        CELL_UPDATE,
        CELL_ARCHIVE,
        MEMBER_INVITE,
        MEMBER_REMOVE,
        MEMBER_ROLE_CHANGE,
        AGENT_RUN,
        TASK_CREATE,
        TASK_VIEW,
    ),
    "editor": (
        CELL_VIEW,
        AGENT_RUN,
        TASK_CREATE,
        TASK_VIEW,
    ),
    "viewer": (
        CELL_VIEW,
        TASK_VIEW,
    ),
    "billing": (
        BILLING_VIEW,
        BILLING_MANAGE,
        WORKSPACE_VIEW,
    ),
    "guest": (TASK_VIEW,),
}
