"""tasks.tasks — top-level agent-team execution unit.

DDL mirrors contracts/tasks/schema.sql 1:1 (ADR-024 §2). FORCE-RLS via
3-GUC current_setting('app.current_cell_id').

Phase 00.5b Commit 6.
"""

from __future__ import annotations

from alembic import op

revision: str = "tasks_0001_tasks"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("tasks",)
depends_on: tuple[str, ...] = ("multitenancy_0002_cells", "agents_0003_agent_instances")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS tasks;")
    op.execute(
        """
        CREATE TABLE tasks.tasks (
            id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id                  uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            agent_instance_id        uuid NULL REFERENCES agents.agent_instances(id),
            team_preset_id           uuid NULL,
            parent_task_id           uuid NULL REFERENCES tasks.tasks(id) ON DELETE CASCADE,
            initiated_by_user_id     uuid NOT NULL,
            title                    text NOT NULL,
            description              text NOT NULL DEFAULT '',
            input_jsonb              jsonb NOT NULL DEFAULT '{}'::jsonb,
            status                   text NOT NULL DEFAULT 'queued' CHECK (status IN
                                        ('queued','running','waiting_input','succeeded','failed','cancelled','timed_out')),
            priority                 smallint NOT NULL DEFAULT 5,
            started_at               timestamptz NULL,
            completed_at             timestamptz NULL,
            total_cost_credits       numeric(10,4) NOT NULL DEFAULT 0,
            total_input_tokens       bigint NOT NULL DEFAULT 0,
            total_output_tokens      bigint NOT NULL DEFAULT 0,
            created_at               timestamptz NOT NULL DEFAULT now(),
            updated_at               timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX idx_tasks_cell_status_time ON tasks.tasks (cell_id, status, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX idx_tasks_parent ON tasks.tasks (parent_task_id) WHERE parent_task_id IS NOT NULL;"
    )
    op.execute("ALTER TABLE tasks.tasks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks.tasks FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tasks_cell_isolation ON tasks.tasks
            USING (cell_id = current_setting('app.current_cell_id', true)::uuid)
            WITH CHECK (cell_id = current_setting('app.current_cell_id', true)::uuid);
        """
    )
    op.execute("GRANT USAGE ON SCHEMA tasks TO oriion_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON tasks.tasks TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks.tasks;")
    op.execute("DROP SCHEMA IF EXISTS tasks;")
