"""artifacts schema — 7-table envelope model (ADR-038, Phase 01.5).

Envelope design per ADR-038 (judge-panel composite G1 + grafts):

- ``artifacts.artifacts``          — envelope: type/title/tags + ``current_version_num``
  head pointer (graft G3 — plain int, no cyclic FK) + ``deleted_at`` soft-delete.
- ``artifacts.artifact_versions``  — append-only immutable version rows
  (``UNIQUE(artifact_id, version_num)``, XOR storage_kind, **no UPDATE grant** —
  immutability is enforced at the DB privilege level, AC-01.5.2). ``text_export``
  is the future FTS/vector hook (graft G2 — nullable, no backfill needed).
- ``artifacts.yjs_documents``      — live CRDT head (bytea state + state_vector);
  queryable target for the dangling ``tasks.task_artifacts.yjs_document_id``.
- ``artifacts.yjs_updates``        — append log (seq IDENTITY), pruned by compaction.
- ``artifacts.yjs_snapshots``      — immutable snapshot history (no UPDATE grant),
  referenced by ``artifact_versions.yjs_snapshot_id``.
- ``artifacts.s3_objects``         — S3 object lifecycle (graft G3): presign inserts a
  ``pending`` row → ``UNIQUE(bucket, s3_key)`` = transactional key reservation;
  queryable target for the dangling ``tasks.task_artifacts.s3_key``.
- ``artifacts.cell_storage_usage`` — bytes accounting per cell (RQ-20260701-002
  lean B: accounting now, quota enforcement is a billing follow-up).

RLS (ADR-009 house pattern): FORCE ROW LEVEL SECURITY on ALL 7 tables with the
direct predicate ``cell_id = _shared.current_cell_id()`` (USING + WITH CHECK).
``cell_id`` is denormalized onto every child table and pinned by composite
anti-drift FKs ``(parent_id, cell_id) → parent(id, cell_id)`` (graft G2) so a
child row can never claim a different cell than its parent.

``tasks.task_artifacts`` is NOT touched (hard constraint) — its ``s3_key`` /
``yjs_document_id`` columns resolve against these tables without any FK.

Revision ID: artifacts_0001_artifacts_core
Down revision: _shared_0002_current_user_id_helper
Branch label: artifacts (foundation)
"""

from __future__ import annotations

from alembic import op

revision: str = "artifacts_0001_artifacts_core"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("artifacts",)
depends_on: tuple[str, ...] = ("multitenancy_0002_cells",)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS artifacts;")

    # ------------------------------------------------------------------ #
    # 1. artifacts.artifacts — the envelope.
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.artifacts (
            id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id              uuid NOT NULL REFERENCES multitenancy.cells(id)
                                     ON DELETE CASCADE,
            artifact_type        text NOT NULL CHECK (artifact_type IN
                                     ('document','code','asset')),
            title                text NOT NULL,
            tags                 jsonb NOT NULL DEFAULT '[]'::jsonb,
            owner_user_id        uuid NULL,
            created_by_agent_id  uuid NULL,
            current_version_num  int  NOT NULL DEFAULT 0
                                     CHECK (current_version_num >= 0),
            deleted_at           timestamptz NULL,
            created_at           timestamptz NOT NULL DEFAULT now(),
            updated_at           timestamptz NOT NULL DEFAULT now(),
            -- Composite anti-drift FK target (graft G2): children pin (id, cell_id)
            -- so a child row can never reference a parent in another cell.
            CONSTRAINT artifacts_id_cell_uniq UNIQUE (id, cell_id)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_artifacts_cell_created "
        "ON artifacts.artifacts (cell_id, created_at DESC);"
    )
    op.execute(
        "COMMENT ON TABLE artifacts.artifacts IS "
        "'Artifact envelope (ADR-038). current_version_num=0 = no committed versions "
        "yet; head resolution for artifact:// URLs. Soft-delete via deleted_at.';"
    )

    # ------------------------------------------------------------------ #
    # 2. artifacts.s3_objects — S3 lifecycle (created before versions: FK target).
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.s3_objects (
            id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id              uuid NOT NULL REFERENCES multitenancy.cells(id)
                                     ON DELETE CASCADE,
            artifact_id          uuid NOT NULL,
            bucket               text NOT NULL,
            s3_key               text NOT NULL,
            mime_type            text NULL,
            byte_size            bigint NULL,
            content_hash_sha256  text NULL,
            status               text NOT NULL DEFAULT 'pending'
                                     CHECK (status IN ('pending','stored','deleted')),
            created_at           timestamptz NOT NULL DEFAULT now(),
            updated_at           timestamptz NOT NULL DEFAULT now(),
            -- Transactional key reservation (graft G3): presign inserts a pending
            -- row; the unique constraint rejects a duplicate key at reserve time.
            CONSTRAINT s3_objects_bucket_key_uniq UNIQUE (bucket, s3_key),
            CONSTRAINT s3_objects_id_cell_uniq UNIQUE (id, cell_id),
            CONSTRAINT s3_objects_artifact_cell_fk
                FOREIGN KEY (artifact_id, cell_id)
                REFERENCES artifacts.artifacts (id, cell_id) ON DELETE CASCADE
        );
        """
    )
    # tasks.task_artifacts.s3_key (text, no FK) resolves via this index.
    op.execute("CREATE INDEX ix_s3_objects_key ON artifacts.s3_objects (s3_key);")
    op.execute("CREATE INDEX ix_s3_objects_artifact ON artifacts.s3_objects (artifact_id);")
    op.execute(
        "COMMENT ON TABLE artifacts.s3_objects IS "
        "'S3 object lifecycle (ADR-038 graft G3): pending (presigned, reserved key) -> "
        "stored (server-side verified) -> deleted. Queryable target for "
        "tasks.task_artifacts.s3_key.';"
    )

    # ------------------------------------------------------------------ #
    # 3. artifacts.yjs_documents — live CRDT head.
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.yjs_documents (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id            uuid NOT NULL REFERENCES multitenancy.cells(id)
                                   ON DELETE CASCADE,
            artifact_id        uuid NOT NULL,
            state              bytea NOT NULL,
            state_vector       bytea NOT NULL,
            update_count       int NOT NULL DEFAULT 0 CHECK (update_count >= 0),
            last_compacted_at  timestamptz NULL,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT yjs_documents_artifact_uniq UNIQUE (artifact_id),
            CONSTRAINT yjs_documents_id_cell_uniq UNIQUE (id, cell_id),
            CONSTRAINT yjs_documents_artifact_cell_fk
                FOREIGN KEY (artifact_id, cell_id)
                REFERENCES artifacts.artifacts (id, cell_id) ON DELETE CASCADE
        );
        """
    )
    op.execute(
        "COMMENT ON TABLE artifacts.yjs_documents IS "
        "'Live Yjs CRDT head (ADR-038): bytea state + state_vector, merged "
        "synchronously under FOR UPDATE (read-your-writes). Queryable target for "
        "tasks.task_artifacts.yjs_document_id. state/state_vector/updates-log are "
        "reused as-is by the future y-websocket sync server (Wave 2+).';"
    )

    # ------------------------------------------------------------------ #
    # 4. artifacts.yjs_updates — append log, pruned by compaction.
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.yjs_updates (
            seq              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            cell_id          uuid NOT NULL,
            yjs_document_id  uuid NOT NULL,
            update_data      bytea NOT NULL,
            created_at       timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT yjs_updates_document_cell_fk
                FOREIGN KEY (yjs_document_id, cell_id)
                REFERENCES artifacts.yjs_documents (id, cell_id) ON DELETE CASCADE
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_yjs_updates_document_seq "
        "ON artifacts.yjs_updates (yjs_document_id, seq);"
    )

    # ------------------------------------------------------------------ #
    # 5. artifacts.yjs_snapshots — immutable snapshot history.
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.yjs_snapshots (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id          uuid NOT NULL,
            yjs_document_id  uuid NOT NULL,
            state            bytea NOT NULL,
            state_vector     bytea NOT NULL,
            created_at       timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT yjs_snapshots_id_cell_uniq UNIQUE (id, cell_id),
            CONSTRAINT yjs_snapshots_document_cell_fk
                FOREIGN KEY (yjs_document_id, cell_id)
                REFERENCES artifacts.yjs_documents (id, cell_id) ON DELETE CASCADE
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_yjs_snapshots_document_created "
        "ON artifacts.yjs_snapshots (yjs_document_id, created_at DESC);"
    )

    # ------------------------------------------------------------------ #
    # 6. artifacts.artifact_versions — append-only, immutable.
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.artifact_versions (
            id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id              uuid NOT NULL,
            artifact_id          uuid NOT NULL,
            version_num          int  NOT NULL CHECK (version_num >= 1),
            storage_kind         text NOT NULL CHECK (storage_kind IN
                                     ('inline','s3','yjs_snapshot')),
            content_inline       jsonb NULL,
            s3_object_id         uuid NULL,
            yjs_snapshot_id      uuid NULL,
            byte_size            bigint NOT NULL DEFAULT 0 CHECK (byte_size >= 0),
            content_hash_sha256  text NOT NULL DEFAULT '',
            text_export          text NULL,
            created_by_user_id   uuid NULL,
            created_by_agent_id  uuid NULL,
            created_at           timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT artifact_versions_num_uniq UNIQUE (artifact_id, version_num),
            CONSTRAINT artifact_versions_artifact_cell_fk
                FOREIGN KEY (artifact_id, cell_id)
                REFERENCES artifacts.artifacts (id, cell_id) ON DELETE CASCADE,
            CONSTRAINT artifact_versions_s3_cell_fk
                FOREIGN KEY (s3_object_id, cell_id)
                REFERENCES artifacts.s3_objects (id, cell_id),
            CONSTRAINT artifact_versions_snapshot_cell_fk
                FOREIGN KEY (yjs_snapshot_id, cell_id)
                REFERENCES artifacts.yjs_snapshots (id, cell_id),
            CONSTRAINT artifact_versions_storage_xor CHECK (
                (storage_kind = 'inline'       AND content_inline  IS NOT NULL
                    AND s3_object_id IS NULL AND yjs_snapshot_id IS NULL)
             OR (storage_kind = 's3'           AND s3_object_id    IS NOT NULL
                    AND content_inline IS NULL AND yjs_snapshot_id IS NULL)
             OR (storage_kind = 'yjs_snapshot' AND yjs_snapshot_id IS NOT NULL
                    AND content_inline IS NULL AND s3_object_id IS NULL)
            )
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_artifact_versions_artifact "
        "ON artifacts.artifact_versions (artifact_id, version_num DESC);"
    )
    op.execute(
        "COMMENT ON COLUMN artifacts.artifact_versions.storage_kind IS "
        "'Evolution seam (ADR-038 graft G3): Wave-2 ''connector'' / Wave-3 "
        "''gitea_ref'' land as a CHECK-swap on this column, no backfill.';"
    )
    op.execute(
        "COMMENT ON COLUMN artifacts.artifact_versions.text_export IS "
        "'Future FTS/pgvector hook (ADR-038 graft G2): plain-text projection of the "
        "version content, populated lazily by a later phase without backfill.';"
    )
    op.execute(
        "COMMENT ON TABLE artifacts.artifact_versions IS "
        "'Append-only immutable versions (ADR-038): artifact://<cell>/<id>/vN targets. "
        "Immutability enforced by grants (no UPDATE for oriion_app).';"
    )

    # ------------------------------------------------------------------ #
    # 7. artifacts.cell_storage_usage — bytes accounting (RQ-20260701-002 lean B).
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE TABLE artifacts.cell_storage_usage (
            cell_id      uuid PRIMARY KEY REFERENCES multitenancy.cells(id)
                             ON DELETE CASCADE,
            bytes_total  bigint NOT NULL DEFAULT 0 CHECK (bytes_total >= 0),
            updated_at   timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "COMMENT ON TABLE artifacts.cell_storage_usage IS "
        "'Per-cell stored-bytes accounting (ADR-038). Enforcement of ADR-012 plan "
        "quotas is a billing follow-up (RQ-20260701-002); this table only counts.';"
    )

    # ------------------------------------------------------------------ #
    # updated_at triggers (reuse the _shared helper, like memory/billing).
    # ------------------------------------------------------------------ #
    for tbl, trigger in (
        ("artifacts.artifacts", "artifacts_set_updated_at"),
        ("artifacts.s3_objects", "s3_objects_set_updated_at"),
        ("artifacts.yjs_documents", "yjs_documents_set_updated_at"),
        ("artifacts.cell_storage_usage", "cell_storage_usage_set_updated_at"),
    ):
        op.execute(
            f"""
            CREATE TRIGGER {trigger}
                BEFORE UPDATE ON {tbl}
                FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
            """
        )

    # ------------------------------------------------------------------ #
    # FORCE-RLS — direct cell isolation via _shared.current_cell_id() on ALL 7.
    # ------------------------------------------------------------------ #
    for tbl, policy in (
        ("artifacts.artifacts", "artifacts_cell_isolation"),
        ("artifacts.artifact_versions", "artifact_versions_cell_isolation"),
        ("artifacts.yjs_documents", "yjs_documents_cell_isolation"),
        ("artifacts.yjs_updates", "yjs_updates_cell_isolation"),
        ("artifacts.yjs_snapshots", "yjs_snapshots_cell_isolation"),
        ("artifacts.s3_objects", "s3_objects_cell_isolation"),
        ("artifacts.cell_storage_usage", "cell_storage_usage_cell_isolation"),
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

    # ------------------------------------------------------------------ #
    # Grants — immutability of versions/snapshots enforced HERE (no UPDATE;
    # AC-01.5.2). FK cascades still work: RI actions run as the table owner.
    # ------------------------------------------------------------------ #
    op.execute("GRANT USAGE ON SCHEMA artifacts TO oriion_app;")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON artifacts.artifacts TO oriion_app;"
    )  # no DELETE: envelope removal is soft-delete (deleted_at) only
    op.execute(
        "GRANT SELECT, INSERT ON artifacts.artifact_versions TO oriion_app;"
    )  # append-only + immutable: no UPDATE, no DELETE
    op.execute("GRANT SELECT, INSERT, UPDATE ON artifacts.yjs_documents TO oriion_app;")
    op.execute(
        "GRANT SELECT, INSERT, DELETE ON artifacts.yjs_updates TO oriion_app;"
    )  # DELETE = compaction pruning of the append log
    op.execute(
        "GRANT SELECT, INSERT ON artifacts.yjs_snapshots TO oriion_app;"
    )  # immutable history: no UPDATE, no DELETE
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON artifacts.s3_objects TO oriion_app;"
    )  # UPDATE = lifecycle transitions; DELETE = janitor pruning of stale pending
    op.execute("GRANT SELECT, INSERT, UPDATE ON artifacts.cell_storage_usage TO oriion_app;")


def downgrade() -> None:
    # Children first (FKs), then parents, then the schema.
    op.execute("DROP TABLE IF EXISTS artifacts.artifact_versions;")
    op.execute("DROP TABLE IF EXISTS artifacts.yjs_snapshots;")
    op.execute("DROP TABLE IF EXISTS artifacts.yjs_updates;")
    op.execute("DROP TABLE IF EXISTS artifacts.yjs_documents;")
    op.execute("DROP TABLE IF EXISTS artifacts.s3_objects;")
    op.execute("DROP TABLE IF EXISTS artifacts.cell_storage_usage;")
    op.execute("DROP TABLE IF EXISTS artifacts.artifacts;")
    op.execute("DROP SCHEMA IF EXISTS artifacts;")
