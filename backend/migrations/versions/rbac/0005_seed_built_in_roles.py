"""Seed: built-in roles + 15 core permissions + role→permission grants.

Materializes the Wave 0 authoritative seed block from
contracts/rbac/schema.sql (commented-out section in the contract; this
migration uncomments and executes it). Per contract README invariant 2 the
inserted rows are immutable; adding new roles/permissions requires another
migration + ADR.

Role→permission grant matrix per phase-spec:

    owner    → all 15
    admin    → cell.* + member.* + agent.run + task.*
    editor   → cell.view + agent.run + task.create + task.view
    viewer   → cell.view + task.view
    billing  → billing.* + workspace.view
    guest    → task.view

NOTE: the seed permissions include `workspace.view/update/delete`
(post-2026-05-19 rename; the legacy contract block used `organization.*`).
Per ADR-024 naming amendment, new code MUST use `workspace.*` slugs.

Revision ID: rbac_0005_seed_built_in_roles
Down revision: rbac_0004_role_assignments
Branch label: rbac (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "rbac_0005_seed_built_in_roles"
down_revision: str | None = "rbac_0004_role_assignments"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


# ── canonical seed payloads ─────────────────────────────────────────────────
# These four constants exist only inside this migration so the seed values
# stay versioned in the alembic history. Mirror them in src/rbac/permissions.py
# at the module level for application-side use.

_ROLES: tuple[tuple[str, str, str], ...] = (
    ("owner", "Owner", "Full control of the workspace including billing."),
    ("admin", "Admin", "Full control of a cell; no billing/workspace-delete."),
    (
        "editor",
        "Editor",
        "Create / run tasks and agents; manage non-billing settings.",
    ),
    ("viewer", "Viewer", "Read-only access to cell content."),
    (
        "billing",
        "Billing",
        "View invoices and manage payment methods; no content access.",
    ),
    (
        "guest",
        "Guest",
        "Time-boxed limited access (e.g. for friends-loop participants).",
    ),
)

_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    ("workspace.view", "View workspace", "workspace", "Read workspace metadata."),
    ("workspace.update", "Edit workspace", "workspace", "Mutate workspace metadata."),
    (
        "workspace.delete",
        "Delete workspace",
        "workspace",
        "Soft-delete the workspace.",
    ),
    ("cell.create", "Create cell", "cell", "Create a new cell in the workspace."),
    ("cell.view", "View cell", "cell", "Read cell metadata."),
    ("cell.update", "Edit cell", "cell", "Mutate cell metadata / settings."),
    ("cell.archive", "Archive cell", "cell", "Archive a cell."),
    ("member.invite", "Invite member", "member", "Issue invitations."),
    ("member.remove", "Remove member", "member", "Remove a member from a cell."),
    (
        "member.role_change",
        "Change member role",
        "member",
        "Reassign a member to a different system role.",
    ),
    ("billing.view", "View billing", "billing", "Read invoices and balances."),
    (
        "billing.manage",
        "Manage billing",
        "billing",
        "Manage payment methods and plan tier.",
    ),
    ("agent.run", "Run agent", "agent", "Trigger an AI agent run."),
    ("task.create", "Create task", "task", "Create a new task."),
    ("task.view", "View task", "task", "Read a task and its artefacts."),
)

# Role-slug → tuple of permission-slugs.
_ROLE_PERMS: dict[str, tuple[str, ...]] = {
    "owner": tuple(p[0] for p in _PERMISSIONS),  # all 15
    "admin": (
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
    ),
    "editor": (
        "cell.view",
        "agent.run",
        "task.create",
        "task.view",
    ),
    "viewer": (
        "cell.view",
        "task.view",
    ),
    "billing": (
        "billing.view",
        "billing.manage",
        "workspace.view",
    ),
    "guest": ("task.view",),
}


def upgrade() -> None:
    # 1. Roles ---------------------------------------------------------------
    for slug, display, desc in _ROLES:
        op.execute(
            f"""
            INSERT INTO rbac.system_roles (slug, display_name, description, is_built_in)
            VALUES ($${slug}$$, $${display}$$, $${desc}$$, true)
            ON CONFLICT (slug) DO NOTHING;
            """  # noqa: S608 — slug/display/desc are module-level literals, not user input
        )

    # 2. Permissions ---------------------------------------------------------
    for slug, display, category, desc in _PERMISSIONS:
        op.execute(
            f"""
            INSERT INTO rbac.permissions (slug, display_name, category, description)
            VALUES ($${slug}$$, $${display}$$, $${category}$$, $${desc}$$)
            ON CONFLICT (slug) DO NOTHING;
            """  # noqa: S608 — literals only
        )

    # 3. Bridge rows ---------------------------------------------------------
    # Resolve role/permission ids by slug (single statement per role keeps the
    # migration readable; ON CONFLICT covers re-runs).
    for role_slug, perm_slugs in _ROLE_PERMS.items():
        perm_list_sql = ", ".join(f"$${s}$$" for s in perm_slugs)
        op.execute(
            f"""
            INSERT INTO rbac.role_permissions (role_id, permission_id)
            SELECT r.id, p.id
              FROM rbac.system_roles r
              CROSS JOIN rbac.permissions p
             WHERE r.slug = $${role_slug}$$
               AND p.slug IN ({perm_list_sql})
            ON CONFLICT (role_id, permission_id) DO NOTHING;
            """  # noqa: S608 — literals only
        )


def downgrade() -> None:
    # Reverse the bridge first to avoid FK conflicts.
    perm_slugs_all = ", ".join(f"$${p[0]}$$" for p in _PERMISSIONS)
    role_slugs_all = ", ".join(f"$${r[0]}$$" for r in _ROLES)
    op.execute(
        f"""
        DELETE FROM rbac.role_permissions
         WHERE role_id IN (SELECT id FROM rbac.system_roles WHERE slug IN ({role_slugs_all}));
        """  # noqa: S608
    )
    op.execute(
        f"DELETE FROM rbac.permissions WHERE slug IN ({perm_slugs_all});"  # noqa: S608
    )
    op.execute(
        f"DELETE FROM rbac.system_roles WHERE slug IN ({role_slugs_all});"  # noqa: S608
    )
