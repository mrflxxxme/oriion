"""memory.conversation_history — per agent-instance message log (FIFO + summary).

Phase 01.4, Wave 1 (ADR-011, grill 2026-06-23 Q2 — conversation history pulled
into the Wave-1 slice). Append-only message log per (cell, agent); the service
keeps the last N=50 as a FIFO window and (when a summarizer is wired)
distils the overflow into a ``memory.memory_entries`` row tagged
``kind='conversation_summary'`` before trimming.

``seq`` is a monotonic IDENTITY column: ``created_at`` defaults to ``now()`` =
transaction time, so multiple messages appended in ONE transaction share a
timestamp and cannot be FIFO-ordered by it. ``seq`` gives a stable insertion
order regardless of transaction batching.

Retention: ADR-011 sets a 90-day conversation-history default (settable per
cell). The Wave-1 slice ships storage + FIFO trim; the time-based retention
sweep is deferred (documented, not yet a job).

RLS: cell-isolation via ``_shared.current_cell_id()`` (FORCE). Messages are
immutable — no ``updated_at`` / trigger.

Revision ID: memory_0002_conversation_history
Down revision: memory_0001_memory_core
Branch label: memory (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "memory_0002_conversation_history"
down_revision: str | None = "memory_0001_memory_core"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] = ("agents_0003_agent_instances",)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE memory.conversation_history (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            seq          bigint GENERATED ALWAYS AS IDENTITY,
            cell_id      uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            workspace_id uuid NOT NULL,
            agent_id     uuid NOT NULL REFERENCES agents.agent_instances(id) ON DELETE CASCADE,
            role         text NOT NULL CHECK (role IN ('user','agent','system')),
            content      text NOT NULL,
            token_count  int  NULL,
            created_at   timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_conversation_cell_agent_seq "
        "ON memory.conversation_history (cell_id, agent_id, seq);"
    )
    op.execute(
        "COMMENT ON TABLE memory.conversation_history IS "
        "'Per agent-instance conversation log (ADR-011 Wave-1). FIFO window of 50 "
        "+ summarize-on-overflow. Cell-isolated via RLS. 90-day retention deferred.';"
    )

    op.execute("ALTER TABLE memory.conversation_history ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE memory.conversation_history FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY conversation_history_cell_isolation ON memory.conversation_history
            USING (cell_id = _shared.current_cell_id())
            WITH CHECK (cell_id = _shared.current_cell_id());
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON memory.conversation_history TO oriion_app;")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS conversation_history_cell_isolation "
        "ON memory.conversation_history;"
    )
    op.execute("DROP TABLE IF EXISTS memory.conversation_history;")
