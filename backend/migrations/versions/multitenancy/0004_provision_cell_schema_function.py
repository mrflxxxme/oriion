"""multitenancy.provision_cell_schema(uuid) — per-cell schema provisioner.

Per ADR-009 amendment 2026-05-19 (eager cell provisioning): when a cell is
created we materialize a dedicated Postgres schema `cell_<uuid_underscored>`
containing the per-cell hot tables (memory_entries with pgvector embeddings
+ HNSW index).

Idempotent: CREATE SCHEMA / CREATE TABLE / CREATE INDEX use IF NOT EXISTS
where possible; the function returns the schema name regardless of whether
it was created fresh or already existed (matches the AC2 < 30s target).

Cell archive does NOT drop the schema — retention is 3 years per FZ-152.

Embedding dimensions: 1024 default (matches the Wave 0 LLM gateway BGE-M3
preset). embedding_dim CHECK ≤ 1024 leaves headroom for shorter models
without re-issuing the CHECK; widening to >1024 requires a migration + ADR.

Revision ID: multitenancy_0004_provision_cell_schema_function
Down revision: multitenancy_0003_cell_members
Branch label: multitenancy (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "multitenancy_0004_provision_cell_schema_function"
down_revision: str | None = "multitenancy_0003_cell_members"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # The function runs as SECURITY DEFINER so the app role (which holds USAGE
    # on multitenancy.* but cannot CREATE SCHEMA) can provision per-cell
    # schemas via call. Owner = role running the migration (db superuser /
    # alembic role) — set search_path explicitly to defeat SP injection.
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

            -- Postgres identifiers can't contain hyphens unless quoted; we
            -- replace `-` with `_` and prefix with `cell_` to get a stable,
            -- unambiguous identifier matching `^cell_[0-9a-f_]{36}$`.
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

            -- HNSW index (pgvector). m=16 / ef_construction=64 are the Wave 0
            -- defaults validated against the 1k-row smoke benchmark. Tunable
            -- via separate migration if recall/latency targets shift.
            EXECUTE format($idx$
                CREATE INDEX IF NOT EXISTS memory_entries_embedding_hnsw_idx
                    ON %s.memory_entries
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
            $idx$, qualified);

            -- Per-cell GRANTs to the app role. USAGE on schema + DML on the
            -- table. We do NOT grant CREATE — table additions go through
            -- alembic migrations only.
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

    op.execute("GRANT EXECUTE ON FUNCTION multitenancy.provision_cell_schema(uuid) TO oriion_app;")

    op.execute(
        "COMMENT ON FUNCTION multitenancy.provision_cell_schema(uuid) IS "
        "'Eagerly provisions a cell_<uuid> schema + memory_entries table + HNSW index. "
        "Idempotent; safe to re-call. Per ADR-009 amendment 2026-05-19.';"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS multitenancy.provision_cell_schema(uuid);")
