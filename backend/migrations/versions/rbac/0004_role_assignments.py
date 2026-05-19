"""rbac.role_assignments — user ↔ scope ↔ role binding.

DDL matches contracts/rbac/schema.sql 1:1 (authoritative per ADR-024).
scope_type enum is `('workspace','cell')` post-2026-05-19 rename
(`organization` retired). Cross-context FKs declared in comments and
validated at the app layer (ADR-024 Consequences).

RLS: role_assignments_select_self — user sees their own assignments only.
Admin visibility goes through BYPASSRLS service-account procedures whose
authorization is enforced application-side via *.admin permissions.

Revision ID: rbac_0004_role_assignments
Down revision: rbac_0003_role_permissions
Branch label: rbac (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "rbac_0004_role_assignments"
down_revision: str | None = "rbac_0003_role_permissions"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE rbac.role_assignments (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id      uuid NOT NULL,
            scope_type   text NOT NULL CHECK (scope_type IN ('workspace','cell')),
            scope_id     uuid NOT NULL,
            role_id      uuid NOT NULL
                REFERENCES rbac.system_roles(id) ON DELETE RESTRICT,
            assigned_by  uuid,
            assigned_at  timestamptz NOT NULL DEFAULT now(),
            expires_at   timestamptz
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX role_assignments_unique_uidx
            ON rbac.role_assignments (user_id, scope_type, scope_id, role_id);
        """
    )
    op.execute("CREATE INDEX role_assignments_user_idx ON rbac.role_assignments (user_id);")
    op.execute(
        "CREATE INDEX role_assignments_scope_idx "
        "ON rbac.role_assignments (scope_type, scope_id);"
    )
    op.execute(
        """
        CREATE INDEX role_assignments_expiring_idx
            ON rbac.role_assignments (expires_at)
            WHERE expires_at IS NOT NULL;
        """
    )

    op.execute(
        "COMMENT ON COLUMN rbac.role_assignments.user_id IS "
        "'Cross-context FK → iam.users.id (not enforced as DB constraint).';"
    )
    op.execute(
        "COMMENT ON COLUMN rbac.role_assignments.scope_id IS "
        "'Cross-context FK → multitenancy.workspaces.id OR .cells.id (per scope_type).';"
    )
    op.execute(
        "COMMENT ON COLUMN rbac.role_assignments.assigned_by IS "
        "'Cross-context FK → iam.users.id; NULL for system / bootstrap assignments.';"
    )

    # RLS — user sees their own assignments unconditionally.
    op.execute("ALTER TABLE rbac.role_assignments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE rbac.role_assignments FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY role_assignments_select_self
            ON rbac.role_assignments
            FOR SELECT
            USING (user_id = _shared.current_user_id());
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON rbac.role_assignments TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS role_assignments_select_self ON rbac.role_assignments;")
    op.execute("DROP TABLE IF EXISTS rbac.role_assignments;")
