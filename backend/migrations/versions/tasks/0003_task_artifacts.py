"""tasks.task_artifacts — outputs produced by a task or step.

Phase 00.5b Commit 6.
"""

from __future__ import annotations

from alembic import op

revision: str = "tasks_0003_task_artifacts"
down_revision: str | None = "tasks_0002_task_steps"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tasks.task_artifacts (
            id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id              uuid NOT NULL REFERENCES tasks.tasks(id) ON DELETE CASCADE,
            step_id              uuid NULL REFERENCES tasks.task_steps(id) ON DELETE SET NULL,
            artifact_type        text NOT NULL CHECK (artifact_type IN
                                    ('text','image','file','structured_data','code')),
            storage_kind         text NOT NULL DEFAULT 'inline' CHECK (storage_kind IN
                                    ('inline','s3','yjs_document')),
            content_inline       jsonb NULL,
            s3_key               text  NULL,
            yjs_document_id      uuid  NULL,
            mime_type            text NOT NULL DEFAULT 'text/markdown',
            byte_size            bigint NOT NULL DEFAULT 0,
            content_hash_sha256  text NOT NULL DEFAULT '',
            created_at           timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT task_artifacts_storage_xor CHECK (
                (storage_kind = 'inline'       AND content_inline   IS NOT NULL AND s3_key IS NULL     AND yjs_document_id IS NULL)
             OR (storage_kind = 's3'           AND s3_key           IS NOT NULL AND content_inline IS NULL AND yjs_document_id IS NULL)
             OR (storage_kind = 'yjs_document' AND yjs_document_id IS NOT NULL AND content_inline IS NULL AND s3_key IS NULL)
            )
        );
        """
    )
    op.execute(
        "CREATE INDEX idx_task_artifacts_task ON tasks.task_artifacts (task_id, created_at DESC);"
    )
    op.execute("ALTER TABLE tasks.task_artifacts ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks.task_artifacts FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY task_artifacts_via_task ON tasks.task_artifacts
            USING (EXISTS (
                SELECT 1 FROM tasks.tasks t
                WHERE t.id = task_artifacts.task_id
                  AND t.cell_id = current_setting('app.current_cell_id', true)::uuid
            ));
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON tasks.task_artifacts TO oriion_app;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks.task_artifacts;")
