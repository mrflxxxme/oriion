"""tasks.outbox — transactional outbox for domain CloudEvents (AC-W1-4).

A domain event is INSERTed into ``tasks.outbox`` in the same transaction as the
state change that produced it; the relay (``runtime.queue.outbox_relay``) drains
unpublished rows and republishes them at-least-once, stamping ``published_at``.
``ce_id`` is UNIQUE (downstream idempotency key). The partial index keeps the
relay's "unpublished, oldest-first" scan cheap.
"""

from __future__ import annotations

from alembic import op

revision: str = "tasks_0005_outbox"
down_revision: str | None = "tasks_0004_task_dispatched_at"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tasks.outbox (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            ce_id           uuid NOT NULL DEFAULT gen_random_uuid(),
            ce_type         text NOT NULL,
            ce_source       text NOT NULL,
            ce_subject      text NULL,
            correlation_id  text NULL,
            data            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            published_at    timestamptz NULL,
            CONSTRAINT outbox_ce_id_unique UNIQUE (ce_id)
        );
        """
    )
    op.execute(
        "CREATE INDEX idx_outbox_unpublished ON tasks.outbox (created_at) "
        "WHERE published_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks.outbox;")
