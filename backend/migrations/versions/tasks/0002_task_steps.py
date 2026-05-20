"""tasks.task_steps — ordered atomic operations within a task.

Phase 00.5b Commit 6.
"""

from __future__ import annotations

from alembic import op

revision: str = "tasks_0002_task_steps"
down_revision: str | None = "tasks_0001_tasks"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tasks.task_steps (
            id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id              uuid NOT NULL REFERENCES tasks.tasks(id) ON DELETE CASCADE,
            step_index           int  NOT NULL,
            agent_archetype_id   uuid NOT NULL REFERENCES agents.agent_archetypes(id),
            step_type            text NOT NULL CHECK (step_type IN
                                    ('llm_call','tool_use','user_input','wait','branch','merge','delegation')),
            input_jsonb          jsonb NOT NULL DEFAULT '{}'::jsonb,
            output_jsonb         jsonb NOT NULL DEFAULT '{}'::jsonb,
            status               text NOT NULL DEFAULT 'queued' CHECK (status IN
                                    ('queued','running','waiting_input','succeeded','failed','skipped','cancelled')),
            started_at           timestamptz NULL,
            completed_at         timestamptz NULL,
            cost_credits         numeric(10,4) NOT NULL DEFAULT 0,
            error_jsonb          jsonb NULL,
            CONSTRAINT task_steps_unique_index UNIQUE (task_id, step_index)
        );
        """
    )
    op.execute(
        "CREATE INDEX idx_task_steps_task_status ON tasks.task_steps (task_id, status, step_index);"
    )
    op.execute("ALTER TABLE tasks.task_steps ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks.task_steps FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY task_steps_via_task ON tasks.task_steps
            USING (EXISTS (
                SELECT 1 FROM tasks.tasks t
                WHERE t.id = task_steps.task_id
                  AND t.cell_id = current_setting('app.current_cell_id', true)::uuid
            ));
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON tasks.task_steps TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks.task_steps;")
