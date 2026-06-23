"""memory.memory_entries + memory.role_memory_entries — cell & role memory.

Phase 01.4, Wave 1 (ADR-011). Two-level manual-control memory:

- ``memory.memory_entries``      — shared cell knowledge base (facts, glossary,
  conversation summaries). RAG-recallable by every agent in the cell.
- ``memory.role_memory_entries`` — per agent-instance personal memory
  (preferences, style/process patterns), scoped additionally by ``agent_id``.

Schema model (grill 2026-06-23, Q3): a SINGLE ``memory`` schema with a
``cell_id`` column + FORCE-RLS via ``_shared.current_cell_id()`` — mirrors the
dominant billing/iam/tasks pattern, NOT the per-cell ``cell_<uuid>`` schema.
This SUPERSEDES the unused 1024-dim ``memory_entries`` placeholder created by
``multitenancy/0004_provision_cell_schema_function`` (see ADR-011 Wave-1 note;
that placeholder is divergent + unused and is slated for cleanup).

Embedding dimension (grill Q1): ``vector(256)`` — YandexGPT text embeddings
(``text-search-doc`` / ``text-search-query``) are 256-dim. The dimension is a
single source of truth: ``src.memory.models.MEMORY_EMBEDDING_DIM``. Changing it
later requires re-embedding + a reindex migration.

RLS: cell-isolation via ``_shared.current_cell_id()`` (returns NULL on
empty/invalid GUC ⇒ default-deny). USING + WITH CHECK both keyed on the active
tenant cell (same contract as billing.subscriptions / tasks.tasks).

Revision ID: memory_0001_memory_core
Down revision: _shared_0002_current_user_id_helper
Branch label: memory (foundation)
"""

from __future__ import annotations

from alembic import op

revision: str = "memory_0001_memory_core"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("memory",)
depends_on: tuple[str, ...] = ("multitenancy_0002_cells", "agents_0003_agent_instances")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS memory;")

    # ------------------------------------------------------------------ #
    # Cell memory — shared knowledge base, recallable by any cell agent.
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE memory.memory_entries (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id             uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            workspace_id        uuid NOT NULL,
            kind                text NOT NULL DEFAULT 'fact'
                                    CHECK (kind IN ('fact','note','glossary','conversation_summary')),
            title               text NULL,
            content             text NOT NULL,
            embedding           vector(256) NULL,
            embedding_model     text NULL,
            tags                jsonb NOT NULL DEFAULT '[]'::jsonb,
            source              text NOT NULL DEFAULT 'manual'
                                    CHECK (source IN ('manual','filter_agent','summary')),
            contains_pii        boolean NOT NULL DEFAULT false,
            created_by_user_id  uuid NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    # HNSW cosine index (pgvector). m=16 / ef_construction=64 — Wave-0 defaults
    # validated against the 1k-row smoke benchmark; tunable via a later migration.
    op.execute(
        """
        CREATE INDEX memory_entries_embedding_hnsw_idx
            ON memory.memory_entries
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """
    )
    op.execute(
        "CREATE INDEX ix_memory_entries_cell_created "
        "ON memory.memory_entries (cell_id, created_at DESC);"
    )
    op.execute(
        "COMMENT ON TABLE memory.memory_entries IS "
        "'Cell-level shared memory (ADR-011 Wave-1). 256-dim Yandex embeddings + "
        "HNSW cosine. Cell-isolated via RLS. Supersedes the cell_<uuid> placeholder.';"
    )

    # ------------------------------------------------------------------ #
    # Role memory — per agent-instance personal memory (+ agent_id filter).
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE memory.role_memory_entries (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id             uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            workspace_id        uuid NOT NULL,
            agent_id            uuid NOT NULL REFERENCES agents.agent_instances(id) ON DELETE CASCADE,
            kind                text NOT NULL DEFAULT 'preference'
                                    CHECK (kind IN ('preference','style','process','fact','note')),
            title               text NULL,
            content             text NOT NULL,
            embedding           vector(256) NULL,
            embedding_model     text NULL,
            tags                jsonb NOT NULL DEFAULT '[]'::jsonb,
            source              text NOT NULL DEFAULT 'manual'
                                    CHECK (source IN ('manual','filter_agent','summary')),
            contains_pii        boolean NOT NULL DEFAULT false,
            created_by_user_id  uuid NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX role_memory_entries_embedding_hnsw_idx
            ON memory.role_memory_entries
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """
    )
    op.execute(
        "CREATE INDEX ix_role_memory_cell_agent_created "
        "ON memory.role_memory_entries (cell_id, agent_id, created_at DESC);"
    )
    op.execute(
        "COMMENT ON TABLE memory.role_memory_entries IS "
        "'Per agent-instance personal memory (ADR-011 Wave-1). Scoped by cell_id "
        "(RLS) + agent_id. 256-dim Yandex embeddings + HNSW cosine.';"
    )

    # ------------------------------------------------------------------ #
    # updated_at triggers (reuse the _shared helper, like billing).
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TRIGGER memory_entries_set_updated_at
            BEFORE UPDATE ON memory.memory_entries
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER role_memory_entries_set_updated_at
            BEFORE UPDATE ON memory.role_memory_entries
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # FORCE-RLS — cell isolation via _shared.current_cell_id().
    # ------------------------------------------------------------------ #
    for tbl, policy in (
        ("memory.memory_entries", "memory_entries_cell_isolation"),
        ("memory.role_memory_entries", "role_memory_entries_cell_isolation"),
    ):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE  ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {policy} ON {tbl}
                USING (cell_id = _shared.current_cell_id())
                WITH CHECK (cell_id = _shared.current_cell_id());
            """
        )

    op.execute("GRANT USAGE ON SCHEMA memory TO oriion_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON memory.memory_entries TO oriion_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON memory.role_memory_entries TO oriion_app;")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS role_memory_entries_cell_isolation " "ON memory.role_memory_entries;"
    )
    op.execute("DROP POLICY IF EXISTS memory_entries_cell_isolation ON memory.memory_entries;")
    op.execute(
        "DROP TRIGGER IF EXISTS role_memory_entries_set_updated_at "
        "ON memory.role_memory_entries;"
    )
    op.execute("DROP TRIGGER IF EXISTS memory_entries_set_updated_at ON memory.memory_entries;")
    op.execute("DROP TABLE IF EXISTS memory.role_memory_entries;")
    op.execute("DROP TABLE IF EXISTS memory.memory_entries;")
    op.execute("DROP SCHEMA IF EXISTS memory;")
