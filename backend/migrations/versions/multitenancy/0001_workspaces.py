"""multitenancy.workspaces — billing / legal tenant.

DDL matches contracts/multitenancy/schema.sql 1:1 (authoritative per ADR-024,
naming-bridge amendment 2026-05-19: was `organizations`).

Revision ID: multitenancy_0001_workspaces
Down revision: _shared_0002_current_user_id_helper
Branch label: multitenancy
"""

from __future__ import annotations

from alembic import op

revision: str = "multitenancy_0001_workspaces"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("multitenancy",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE multitenancy.workspaces (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            slug            text NOT NULL,
            display_name    text NOT NULL,
            billing_email   citext,
            country_code    char(2) NOT NULL DEFAULT 'RU',
            timezone        text NOT NULL DEFAULT 'Europe/Moscow',
            plan_tier       text NOT NULL DEFAULT 'free'
                CHECK (plan_tier IN ('free','starter','pro','enterprise')),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX workspaces_slug_active_uidx
            ON multitenancy.workspaces (slug)
            WHERE deleted_at IS NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX workspaces_plan_tier_idx
            ON multitenancy.workspaces (plan_tier)
            WHERE deleted_at IS NULL;
        """
    )

    op.execute(
        "COMMENT ON TABLE multitenancy.workspaces IS "
        "'Billing / legal tenant (was `organizations` pre-2026-05-19). "
        "Soft-delete cascades cells to archived state.';"
    )

    op.execute(
        """
        CREATE TRIGGER workspaces_set_updated_at
            BEFORE UPDATE ON multitenancy.workspaces
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # RLS — membership-driven visibility (see contract README "RLS — 3-GUC layered model").
    op.execute("ALTER TABLE multitenancy.workspaces ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE multitenancy.workspaces FORCE  ROW LEVEL SECURITY;")
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

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON multitenancy.workspaces TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workspaces_select_own ON multitenancy.workspaces;")
    op.execute("DROP TRIGGER IF EXISTS workspaces_set_updated_at ON multitenancy.workspaces;")
    op.execute("DROP TABLE IF EXISTS multitenancy.workspaces;")
