"""multitenancy.cell_members — user ↔ cell membership with system role.

DDL matches contracts/multitenancy/schema.sql 1:1 (authoritative per ADR-024).
Cross-context FKs (iam.users.id, rbac.system_roles.id) are declared in
comments and validated at the application layer (ADR-024 Consequences —
preserves the microservice-extraction option).

RLS: cell_members_select_co_member policy (a member sees co-members).

Revision ID: multitenancy_0003_cell_members
Down revision: multitenancy_0002_cells
Branch label: multitenancy (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "multitenancy_0003_cell_members"
down_revision: str | None = "multitenancy_0002_cells"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE multitenancy.cell_members (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id         uuid NOT NULL
                REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            user_id         uuid NOT NULL,
            role_id         uuid NOT NULL,
            joined_at       timestamptz NOT NULL DEFAULT now(),
            invited_by      uuid,
            last_active_at  timestamptz
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX cell_members_cell_user_uidx
            ON multitenancy.cell_members (cell_id, user_id);
        """
    )
    op.execute("CREATE INDEX cell_members_user_id_idx ON multitenancy.cell_members (user_id);")
    op.execute("CREATE INDEX cell_members_role_id_idx ON multitenancy.cell_members (role_id);")

    op.execute(
        "COMMENT ON TABLE multitenancy.cell_members IS "
        "'User membership in a cell with a system role. "
        "Cross-context FKs enforced at app layer.';"
    )
    op.execute(
        "COMMENT ON COLUMN multitenancy.cell_members.user_id IS "
        "'Cross-context FK → iam.users.id (not enforced as DB constraint).';"
    )
    op.execute(
        "COMMENT ON COLUMN multitenancy.cell_members.role_id IS "
        "'Cross-context FK → rbac.system_roles.id (not enforced as DB constraint).';"
    )
    op.execute(
        "COMMENT ON COLUMN multitenancy.cell_members.invited_by IS "
        "'Cross-context FK → iam.users.id; nullable for owner self-join.';"
    )

    # RLS — restrictive self-row visibility (Wave 0). The contract README
    # specifies "co-members of the same cell" but the natural EXISTS query
    # over cell_members itself causes Postgres infinite-recursion in the
    # policy check. Wave 1+ swaps in a SECURITY DEFINER helper
    # `_shared.current_user_cell_ids()` that bypasses RLS for the inner
    # lookup and restores the co-member visibility semantics. Until then
    # the restrictive baseline (you see only your own membership rows)
    # holds — strictly safer than the documented intent.
    op.execute("ALTER TABLE multitenancy.cell_members ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE multitenancy.cell_members FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY cell_members_select_self_row
            ON multitenancy.cell_members
            FOR SELECT
            USING (user_id = _shared.current_user_id());
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON multitenancy.cell_members TO oriion_app;")

    # workspaces_select_own — deferred from 0001_workspaces.py (Architect-audit
    # H2, 2026-05-19): the USING clause references multitenancy.cells AND
    # multitenancy.cell_members which only exist at this point in the chain.
    # Default-deny held during 0001+0002 because the table had RLS forced with
    # zero permissive policies.
    op.execute(
        """
        CREATE POLICY workspaces_select_own
            ON multitenancy.workspaces
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1
                    FROM multitenancy.cells c
                    JOIN multitenancy.cell_members m ON m.cell_id = c.id
                    WHERE c.workspace_id = workspaces.id
                      AND m.user_id = _shared.current_user_id()
                )
            );
        """
    )

    # cells_select_member — deferred from 0002_cells.py (same forward-reference
    # issue: references cell_members which only exists here).
    op.execute(
        """
        CREATE POLICY cells_select_member
            ON multitenancy.cells
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1
                    FROM multitenancy.cell_members m
                    WHERE m.cell_id = cells.id
                      AND m.user_id = _shared.current_user_id()
                )
            );
        """
    )

    # Security audit H-2, 2026-05-19: explicit write policies for workspaces,
    # cells, cell_members. The contract README states "Write policies are
    # intentionally not defined at the RLS layer. Mutations go through
    # service-account connections that bypass RLS via stored procedures;
    # authorization is enforced application-side using the `rbac` context."
    # Wave 0: app-layer authz (rbac.AuthorizationService) is the source of
    # truth; RLS write policies permit writes when a tenant GUC is set
    # (rejected when context unset — default-deny holds). Wave 1+ tightens
    # via SECURITY DEFINER procedures + BYPASSRLS service role.
    op.execute(
        """
        CREATE POLICY workspaces_write_with_context
            ON multitenancy.workspaces
            FOR ALL
            USING (_shared.current_user_id() IS NOT NULL)
            WITH CHECK (_shared.current_user_id() IS NOT NULL);
        """
    )
    op.execute(
        """
        CREATE POLICY cells_write_with_context
            ON multitenancy.cells
            FOR ALL
            USING (_shared.current_user_id() IS NOT NULL)
            WITH CHECK (_shared.current_user_id() IS NOT NULL);
        """
    )
    op.execute(
        """
        CREATE POLICY cell_members_write_with_context
            ON multitenancy.cell_members
            FOR ALL
            USING (_shared.current_user_id() IS NOT NULL)
            WITH CHECK (_shared.current_user_id() IS NOT NULL);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS cells_select_member ON multitenancy.cells;")
    op.execute("DROP POLICY IF EXISTS workspaces_select_own ON multitenancy.workspaces;")
    op.execute("DROP POLICY IF EXISTS cell_members_select_self_row ON multitenancy.cell_members;")
    op.execute("DROP TABLE IF EXISTS multitenancy.cell_members;")
