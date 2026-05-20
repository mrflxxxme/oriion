"""agents.agent_instances — per-cell instantiations of an archetype.

FORCE-RLS protected via multitenancy.current_cell_id() (Phase 00.5a 3-GUC).

Phase 00.5b Commit 5.
"""

from __future__ import annotations

from alembic import op

revision: str = "agents_0003_agent_instances"
down_revision: str | None = "agents_0002_team_presets"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] = ("multitenancy_0003_cell_members",)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE agents.agent_instances (
            id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id                  uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            agent_archetype_id       uuid NOT NULL REFERENCES agents.agent_archetypes(id),
            custom_name              text NULL,
            custom_settings_jsonb    jsonb NOT NULL DEFAULT '{}'::jsonb,
            total_tasks_completed    int NOT NULL DEFAULT 0,
            last_used_at             timestamptz NULL,
            created_at               timestamptz NOT NULL DEFAULT now(),
            updated_at               timestamptz NOT NULL DEFAULT now(),
            archived_at              timestamptz NULL
        );
        """
    )
    op.execute(
        """
        CREATE INDEX idx_agent_instances_cell_active
            ON agents.agent_instances (cell_id) WHERE archived_at IS NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX idx_agent_instances_archetype
            ON agents.agent_instances (agent_archetype_id);
        """
    )
    # RLS: cell-scoped via 3-GUC app.current_cell_id (Phase 00.5a).
    op.execute("ALTER TABLE agents.agent_instances ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE agents.agent_instances FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY agent_instances_cell_isolation ON agents.agent_instances
            USING (cell_id = current_setting('app.current_cell_id', true)::uuid)
            WITH CHECK (cell_id = current_setting('app.current_cell_id', true)::uuid);
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON agents.agent_instances TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agents.agent_instances;")
