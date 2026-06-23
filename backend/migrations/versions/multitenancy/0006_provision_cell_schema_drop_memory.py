"""multitenancy.provision_cell_schema(uuid) — drop the dead per-cell memory_entries.

Phase 01.4 cleanup (ADR-011 Wave-1). Memory now lives in a SINGLE `memory`
schema (`memory.memory_entries` / `memory.role_memory_entries` /
`memory.conversation_history`, 256-dim, RLS by `cell_id`) — see the ADR-011
Wave-1 implementation-status note. The per-cell `cell_<uuid>.memory_entries`
table that `multitenancy/0004` provisions (1024-dim + HNSW) is therefore
unused/divergent: nothing in `src/` references it, and it is never read or
written.

This migration:
  * recreates `provision_cell_schema` so NEW cells get only the empty
    `cell_<uuid>` schema (+ USAGE grant) — no `memory_entries` table/index/grant;
  * DROPs the dead `memory_entries` from EXISTING `cell_*` schemas. It is safe:
    the table is an unused Wave-0 placeholder (no writer), so `DROP TABLE IF
    EXISTS` over the `^cell_[0-9a-f_]{36}$` schemas reclaims it with no data loss.

The function still returns the schema name and keeps `CREATE SCHEMA IF NOT
EXISTS` (eager per-cell provisioning per ADR-009 stays; only the memory table is
removed). Downgrade restores the 0004 memory-bearing function (existing cells
are NOT re-materialized on downgrade — they re-provision on next call).

Revision ID: multitenancy_0006_provision_cell_schema_drop_memory
Down revision: multitenancy_0005_bootstrap_first_workspace_function
Branch label: multitenancy (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "multitenancy_0006_provision_cell_schema_drop_memory"
down_revision: str | None = "multitenancy_0005_bootstrap_first_workspace_function"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Recreate the provisioner WITHOUT the memory_entries table/index/grants.
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION multitenancy.provision_cell_schema(cell_uuid uuid)
        RETURNS text
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $func$
        DECLARE
            schema_name text;
            qualified   text;
        BEGIN
            IF cell_uuid IS NULL THEN
                RAISE EXCEPTION 'cell_uuid cannot be NULL';
            END IF;

            schema_name := 'cell_' || replace(cell_uuid::text, '-', '_');
            qualified   := quote_ident(schema_name);

            EXECUTE format('CREATE SCHEMA IF NOT EXISTS %s', qualified);
            EXECUTE format('GRANT USAGE ON SCHEMA %s TO oriion_app', qualified);

            RETURN schema_name;
        END;
        $func$;
        """
    )

    op.execute(
        "COMMENT ON FUNCTION multitenancy.provision_cell_schema(uuid) IS "
        "'Eagerly provisions an empty cell_<uuid> schema (+ USAGE grant). "
        "Idempotent. Memory lives in the single `memory` schema since Phase 01.4 "
        "(ADR-011 Wave-1) — the per-cell memory_entries placeholder was removed.';"
    )

    # Reclaim the dead per-cell memory_entries from existing cells. Safe: unused
    # Wave-0 placeholder, no writer. Pattern matches cell_<uuid_underscored>.
    op.execute(
        r"""
        DO $cleanup$
        DECLARE
            sch text;
        BEGIN
            FOR sch IN
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name ~ '^cell_[0-9a-f_]{36}$'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %I.memory_entries', sch);
            END LOOP;
        END
        $cleanup$;
        """
    )


def downgrade() -> None:
    # Restore the 0004 memory-bearing provisioner verbatim.
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION multitenancy.provision_cell_schema(cell_uuid uuid)
        RETURNS text
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $func$
        DECLARE
            schema_name text;
            qualified   text;
        BEGIN
            IF cell_uuid IS NULL THEN
                RAISE EXCEPTION 'cell_uuid cannot be NULL';
            END IF;

            schema_name := 'cell_' || replace(cell_uuid::text, '-', '_');
            qualified   := quote_ident(schema_name);

            EXECUTE format('CREATE SCHEMA IF NOT EXISTS %s', qualified);

            EXECUTE format($ddl$
                CREATE TABLE IF NOT EXISTS %s.memory_entries (
                    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    content             text NOT NULL,
                    embedding           vector(1024),
                    embedding_provider  text NOT NULL,
                    embedding_model     text NOT NULL,
                    embedding_dim       int  NOT NULL CHECK (embedding_dim <= 1024),
                    metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
                    created_at          timestamptz NOT NULL DEFAULT now()
                )
            $ddl$, qualified);

            EXECUTE format($idx$
                CREATE INDEX IF NOT EXISTS memory_entries_embedding_hnsw_idx
                    ON %s.memory_entries
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
            $idx$, qualified);

            EXECUTE format('GRANT USAGE ON SCHEMA %s TO oriion_app', qualified);
            EXECUTE format(
                'GRANT SELECT, INSERT, UPDATE, DELETE ON %s.memory_entries TO oriion_app',
                qualified
            );

            RETURN schema_name;
        END;
        $func$;
        """
    )

    op.execute(
        "COMMENT ON FUNCTION multitenancy.provision_cell_schema(uuid) IS "
        "'Eagerly provisions a cell_<uuid> schema + memory_entries table + HNSW index. "
        "Idempotent; safe to re-call. Per ADR-009 amendment 2026-05-19.';"
    )
