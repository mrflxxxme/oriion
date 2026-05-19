"""_shared bootstrap — extensions, schemas, set_updated_at, oriion_app role.

Architect-PR ownership note
---------------------------
This migration was originally scoped to Phase 00.3 (per the 00.3 phase-spec
inline `bootstrap_schemas.sql`). It was moved into the architect-PR so that
Phases 00.2 / 00.3 / 00.4 can execute in 3-way parallel without each phase
racing to create the same extensions or schemas. Phase 00.3 now starts at
the multitenancy DDL directly, with this migration as its `down_revision`
foundation.

What this creates
-----------------
1. Required PostgreSQL extensions:
   - pgcrypto    (gen_random_uuid())
   - citext      (case-insensitive emails per iam contract invariant 1)
   - uuid-ossp   (additional UUID helpers)
   - vector      (pgvector 0.7+ — agent memory & semantic search)
   - pg_stat_statements (operational observability)
2. Bounded-context schema namespaces (one per ADR-024 §1 context).
3. `_shared.set_updated_at()` trigger function used by every context.
4. `oriion_app` NOLOGIN role with USAGE on every schema (table-level GRANTs
   are issued per-context by each phase's first DDL migration).

Branch label
------------
This revision opens the `_shared` branch. Every bounded-context first
migration MUST set `down_revision = "_shared_0001_init"` to chain its
context branch onto this foundation.

Revision IDs
------------
Revision ID: _shared_0001_init
Down revision: None
Branch label: _shared
Create date: 2026-05-17
"""

from __future__ import annotations

from alembic import op

revision: str = "_shared_0001_init"
down_revision: str | None = None
branch_labels: tuple[str, ...] = ("_shared",)
depends_on: str | None = None


SCHEMAS: tuple[str, ...] = (
    "_shared",
    "iam",
    "multitenancy",
    "rbac",
    "billing",
    "llm_gateway",
    "mcp",
    "agents",
    "tasks",
    "artifacts",
    "memory",
    "audit",
)


def upgrade() -> None:
    # 1. Schemas FIRST (so pg_stat_statements can install into _shared) ------
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}";')

    # 2. Extensions ----------------------------------------------------------
    # Each CREATE EXTENSION IF NOT EXISTS is idempotent; safe under retry.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # pg_stat_statements requires `shared_preload_libraries=pg_stat_statements`
    # on the Postgres cluster (server-restart needed). Yandex Managed Postgres
    # enables it via cluster setting; the dev compose image does NOT preload
    # it by default. Wrap in DO/EXCEPTION so a fresh `make dev-bootstrap` on a
    # vanilla image does not fail — ops will enable it via YC console for prod.
    # Install into _shared to keep oriion_app's USAGE grant aligned.
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA _shared;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pg_stat_statements requires shared_preload_libraries — skipping (ops adds via YC console for prod).';
        END
        $$;
        """
    )

    # 3. set_updated_at() trigger function -----------------------------------
    # Standard pattern: BEFORE UPDATE triggers per table call this to refresh
    # the updated_at column. Idempotent via CREATE OR REPLACE.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION _shared.set_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;
        """
    )

    # 4. oriion_app role -----------------------------------------------------
    # CREATE ROLE has no IF NOT EXISTS in standard Postgres; wrap in DO block
    # so re-running the migration on a half-initialized DB does not fail.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oriion_app') THEN
                CREATE ROLE oriion_app NOLOGIN;
            END IF;
        END
        $$;
        """
    )

    # Grant USAGE on every schema. Table-level GRANTs are per-context.
    schema_list = ", ".join(f'"{s}"' for s in SCHEMAS)
    op.execute(f"GRANT USAGE ON SCHEMA {schema_list} TO oriion_app;")


def downgrade() -> None:
    # Drop in reverse order. Note: extensions are intentionally NOT dropped —
    # other databases on the cluster may share them. Schemas are dropped only
    # if empty (CASCADE deliberately omitted to fail loud if downstream
    # bounded contexts still have tables here).
    op.execute(
        "REVOKE USAGE ON SCHEMA " + ", ".join(f'"{s}"' for s in SCHEMAS) + " FROM oriion_app;"
    )
    op.execute("DROP ROLE IF EXISTS oriion_app;")
    op.execute("DROP FUNCTION IF EXISTS _shared.set_updated_at();")
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" RESTRICT;')
