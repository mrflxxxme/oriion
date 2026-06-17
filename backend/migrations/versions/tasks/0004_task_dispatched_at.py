"""tasks.tasks — add dispatched_at idempotency marker.

Phase 01.1 infra-PR (AC-W1-16a). When POST /tasks/{id}/run enqueues a Dramatiq
actor instead of running inline, the row stays status='queued' until the worker
picks it up and flips it to 'running'. `dispatched_at` records the enqueue moment
so a redelivered/duplicate dispatch is a no-op (the worker guards on
status=='queued') and so a future reconciliation sweeper can find tasks that were
committed-dispatched but whose enqueue was lost (outbox is AC-W1-4, deferred).

Nullable ADD COLUMN — no status CHECK-constraint change (there is deliberately no
'dispatched' status; see ADR-034).
"""

from __future__ import annotations

from alembic import op

revision: str = "tasks_0004_task_dispatched_at"
down_revision: str | None = "tasks_0003_task_artifacts"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE tasks.tasks ADD COLUMN dispatched_at timestamptz NULL;")


def downgrade() -> None:
    op.execute("ALTER TABLE tasks.tasks DROP COLUMN IF EXISTS dispatched_at;")
