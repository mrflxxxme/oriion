"""multitenancy.cells — workspace boundary (= AI team per ADR-009).

DDL matches contracts/multitenancy/schema.sql 1:1 (authoritative per ADR-024).
RLS: cells_select_member policy (visible to its members via EXISTS over
multitenancy.cell_members). Per ADR-009 amendment 2026-05-19, the 3-GUC
layered model — `app.current_user_id` reached through
`_shared.current_user_id()` — drives multitenancy.* policies.

Revision ID: multitenancy_0002_cells
Down revision: multitenancy_0001_workspaces
Branch label: multitenancy (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "multitenancy_0002_cells"
down_revision: str | None = "multitenancy_0001_workspaces"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE multitenancy.cells (
            id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id                uuid NOT NULL
                REFERENCES multitenancy.workspaces(id) ON DELETE RESTRICT,
            slug                        text NOT NULL,
            display_name                text NOT NULL,
            vertical_template_slug      text,
            settings_jsonb              jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now(),
            archived_at                 timestamptz
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX cells_workspace_slug_uidx
            ON multitenancy.cells (workspace_id, slug);
        """
    )
    op.execute(
        """
        CREATE INDEX cells_workspace_id_idx
            ON multitenancy.cells (workspace_id)
            WHERE archived_at IS NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX cells_vertical_template_idx
            ON multitenancy.cells (vertical_template_slug)
            WHERE archived_at IS NULL AND vertical_template_slug IS NOT NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE multitenancy.cells IS "
        "'Workspace = AI team per ADR-009. Archived (soft) on workspace soft-delete.';"
    )
    op.execute(
        "COMMENT ON COLUMN multitenancy.cells.vertical_template_slug IS "
        "'Loose FK to verticals/<slug>/ (string match by convention).';"
    )

    op.execute(
        """
        CREATE TRIGGER cells_set_updated_at
            BEFORE UPDATE ON multitenancy.cells
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # RLS — visible to members (EXISTS over cell_members keyed on current_user_id GUC).
    op.execute("ALTER TABLE multitenancy.cells ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE multitenancy.cells FORCE  ROW LEVEL SECURITY;")
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

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON multitenancy.cells TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS cells_select_member ON multitenancy.cells;")
    op.execute("DROP TRIGGER IF EXISTS cells_set_updated_at ON multitenancy.cells;")
    op.execute("DROP TABLE IF EXISTS multitenancy.cells;")
