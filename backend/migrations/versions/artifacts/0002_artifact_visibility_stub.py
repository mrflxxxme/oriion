"""artifacts.artifacts.visibility stub column (ADR-014 §1, Phase 01.7 RBAC).

Phase 01.7 ships **Option A (flat visibility)**: every cell member sees every
cell artifact (RLS is already by ``cell_id``; Member = cell access). Owner vs
Member differ only in RIGHTS, not content visibility. This migration adds a
**stub** ``visibility`` column to the artifacts envelope so per-artifact privacy
(Option B) can land in a later wave **without an ALTER-under-data**:

    visibility text NOT NULL DEFAULT 'cell-shared'

Design notes:
  * NOT NULL with a literal DEFAULT ⇒ Postgres backfills existing rows with the
    default in the same DDL — **no separate backfill step needed** (the table is
    also empty in Wave-1, but the default keeps this true under data).
  * A CHECK constrains the column to the currently-meaningful value plus the
    forward-declared Option-B value (``private``) so a future phase flips
    behaviour with a policy change, not a schema migration.
  * **NOT enforced anywhere in Wave-1** — no RLS predicate, no application read
    path consults it. It is a pure evolution seam (mirrors the ADR-038 graft
    pattern: ``artifact_versions.text_export`` / ``storage_kind``).

This migration ALTERs an existing table (``artifacts.artifacts``), so the
autonomy tripwire correctly classifies it as **db_migrations → needs founder
ack** (it is not a provable pure-CREATE). That is expected for 01.7.

Revision ID: artifacts_0002_artifact_visibility_stub
Down revision: artifacts_0001_artifacts_core
Branch label: (none — continues the artifacts branch)
"""

from __future__ import annotations

from alembic import op

revision: str = "artifacts_0002_artifact_visibility_stub"
down_revision: str | None = "artifacts_0001_artifacts_core"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Literal DDL (no f-string loop) — the ADD COLUMN with a NOT NULL DEFAULT
    # is a metadata-only rewrite on an empty table and a default-backfill on a
    # populated one; either way no separate UPDATE pass is required.
    op.execute(
        """
        ALTER TABLE artifacts.artifacts
            ADD COLUMN visibility text NOT NULL DEFAULT 'cell-shared';
        """
    )
    op.execute(
        """
        ALTER TABLE artifacts.artifacts
            ADD CONSTRAINT artifacts_visibility_check
            CHECK (visibility IN ('cell-shared', 'private'));
        """
    )
    op.execute(
        "COMMENT ON COLUMN artifacts.artifacts.visibility IS "
        "'Per-artifact privacy seam (ADR-014 §1, Phase 01.7). Wave-1 ships "
        "Option A (flat): all cell members see all artifacts, so this is "
        "ALWAYS ''cell-shared'' and is NOT enforced. ''private'' is forward-"
        "declared for Option B (per-artifact privacy) — a future phase flips "
        "behaviour via an RLS/service change, no ALTER-under-data.';"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE artifacts.artifacts "
        "DROP CONSTRAINT IF EXISTS artifacts_visibility_check;"
    )
    op.execute("ALTER TABLE artifacts.artifacts DROP COLUMN IF EXISTS visibility;")
