-- Context: artifacts — envelope model per ADR-038 (Phase 01.5, Wave 1)
-- Authoritative implementation: backend/migrations/versions/artifacts/0001_artifacts_core.py
-- (this file mirrors it 1:1 per ADR-024 §2)
--
-- Cross-context dependencies:
--   * multitenancy.cells — cell_id is the isolation scope (FORCE RLS)
--   * tasks.task_artifacts — its dangling s3_key / yjs_document_id columns
--     resolve against artifacts.s3_objects.s3_key / artifacts.yjs_documents.id
--     (NO FK — the tasks context is not modified)
--   * _shared.current_cell_id() — RLS predicate helper (3-GUC model, ADR-009)
--   * _shared.set_updated_at() — updated_at trigger helper

CREATE SCHEMA IF NOT EXISTS artifacts;

-- =============================================================================
-- artifacts.artifacts — the envelope (typed, addressable work product)
-- =============================================================================
CREATE TABLE artifacts.artifacts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id              uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    artifact_type        text NOT NULL CHECK (artifact_type IN ('document','code','asset')),
    title                text NOT NULL,
    tags                 jsonb NOT NULL DEFAULT '[]'::jsonb,
    owner_user_id        uuid NULL,
    created_by_agent_id  uuid NULL,
    -- Head pointer for artifact:// URL resolution. 0 = no committed versions.
    -- Plain int (no cyclic FK to artifact_versions) — ADR-038 graft G3.
    current_version_num  int  NOT NULL DEFAULT 0 CHECK (current_version_num >= 0),
    -- Per-artifact privacy seam (ADR-014 §1, Phase 01.7). Wave-1 = Option A
    -- (flat): all cell members see all artifacts → ALWAYS 'cell-shared', NOT
    -- enforced. 'private' is forward-declared for Option B (a later phase flips
    -- behaviour via RLS/service change, no ALTER-under-data). Added by migration
    -- artifacts/0002_artifact_visibility_stub.py.
    visibility           text NOT NULL DEFAULT 'cell-shared'
                             CHECK (visibility IN ('cell-shared','private')),
    deleted_at           timestamptz NULL,          -- soft-delete
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    -- Composite anti-drift FK target (graft G2): children pin (id, cell_id).
    CONSTRAINT artifacts_id_cell_uniq UNIQUE (id, cell_id)
);
CREATE INDEX ix_artifacts_cell_created ON artifacts.artifacts (cell_id, created_at DESC);

-- =============================================================================
-- artifacts.s3_objects — S3 object lifecycle (graft G3)
--   presign inserts 'pending' → UNIQUE(bucket, s3_key) = transactional key
--   reservation → 'stored' after server-side verification → 'deleted'.
--   Queryable target for tasks.task_artifacts.s3_key.
-- =============================================================================
CREATE TABLE artifacts.s3_objects (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id              uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    artifact_id          uuid NOT NULL,
    bucket               text NOT NULL,
    s3_key               text NOT NULL,   -- <env>/<cell_id>/<artifact_id>/<version_num>/<filename>
    mime_type            text NULL,
    byte_size            bigint NULL,     -- server-side, set at complete (client never trusted)
    content_hash_sha256  text NULL,       -- server-side, set at complete
    status               text NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','stored','deleted')),
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT s3_objects_bucket_key_uniq UNIQUE (bucket, s3_key),
    CONSTRAINT s3_objects_id_cell_uniq UNIQUE (id, cell_id),
    CONSTRAINT s3_objects_artifact_cell_fk
        FOREIGN KEY (artifact_id, cell_id)
        REFERENCES artifacts.artifacts (id, cell_id) ON DELETE CASCADE
);
CREATE INDEX ix_s3_objects_key ON artifacts.s3_objects (s3_key);
CREATE INDEX ix_s3_objects_artifact ON artifacts.s3_objects (artifact_id);

-- =============================================================================
-- artifacts.yjs_documents — live CRDT head (bytea + pycrdt, REST-only Wave 1)
--   Merged synchronously under FOR UPDATE (read-your-writes). Queryable target
--   for tasks.task_artifacts.yjs_document_id. state/state_vector/updates-log
--   are reused as-is by the future y-websocket sync server (Wave 2+).
-- =============================================================================
CREATE TABLE artifacts.yjs_documents (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id            uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    artifact_id        uuid NOT NULL,
    state              bytea NOT NULL,   -- full Yjs update encoding of the head
    state_vector       bytea NOT NULL,   -- for future diff sync
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

-- =============================================================================
-- artifacts.yjs_updates — append log (pruned by compaction, never authoritative)
--   Compaction: update_count > 500 OR state > 1 MiB → snapshot + prune log.
-- =============================================================================
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
CREATE INDEX ix_yjs_updates_document_seq ON artifacts.yjs_updates (yjs_document_id, seq);

-- =============================================================================
-- artifacts.yjs_snapshots — immutable snapshot history (checkpoint/compaction)
-- =============================================================================
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
CREATE INDEX ix_yjs_snapshots_document_created
    ON artifacts.yjs_snapshots (yjs_document_id, created_at DESC);

-- =============================================================================
-- artifacts.artifact_versions — append-only, immutable (artifact://.../vN)
--   storage_kind evolution seam (graft G3): Wave-2 'connector' / Wave-3
--   'gitea_ref' land as a CHECK-swap, no backfill.
--   text_export (graft G2): future FTS/pgvector hook, populated lazily.
-- =============================================================================
CREATE TABLE artifacts.artifact_versions (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id              uuid NOT NULL,
    artifact_id          uuid NOT NULL,
    version_num          int  NOT NULL CHECK (version_num >= 1),
    storage_kind         text NOT NULL CHECK (storage_kind IN ('inline','s3','yjs_snapshot')),
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
CREATE INDEX ix_artifact_versions_artifact
    ON artifacts.artifact_versions (artifact_id, version_num DESC);

-- =============================================================================
-- artifacts.cell_storage_usage — bytes accounting (RQ-20260701-002 lean B:
-- accounting now; ADR-012 tariff quota ENFORCEMENT is a billing follow-up)
-- =============================================================================
CREATE TABLE artifacts.cell_storage_usage (
    cell_id      uuid PRIMARY KEY REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    bytes_total  bigint NOT NULL DEFAULT 0 CHECK (bytes_total >= 0),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- updated_at triggers (_shared.set_updated_at, house pattern)
-- =============================================================================
CREATE TRIGGER artifacts_set_updated_at
    BEFORE UPDATE ON artifacts.artifacts
    FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
CREATE TRIGGER s3_objects_set_updated_at
    BEFORE UPDATE ON artifacts.s3_objects
    FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
CREATE TRIGGER yjs_documents_set_updated_at
    BEFORE UPDATE ON artifacts.yjs_documents
    FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
CREATE TRIGGER cell_storage_usage_set_updated_at
    BEFORE UPDATE ON artifacts.cell_storage_usage
    FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();

-- =============================================================================
-- FORCE-RLS — direct cell isolation via _shared.current_cell_id() on ALL 7
-- tables (USING + WITH CHECK; missing GUC ⇒ NULL ⇒ default-deny)
-- =============================================================================
-- For each of: artifacts, artifact_versions, yjs_documents, yjs_updates,
--              yjs_snapshots, s3_objects, cell_storage_usage:
--   ALTER TABLE artifacts.<t> ENABLE ROW LEVEL SECURITY;
--   ALTER TABLE artifacts.<t> FORCE  ROW LEVEL SECURITY;
--   CREATE POLICY <t>_cell_isolation ON artifacts.<t>
--       USING (cell_id = _shared.current_cell_id())
--       WITH CHECK (cell_id = _shared.current_cell_id());

-- =============================================================================
-- Grants — immutability enforced at the privilege level (AC-01.5.2):
-- artifact_versions and yjs_snapshots get NO UPDATE and NO DELETE.
-- =============================================================================
GRANT USAGE ON SCHEMA artifacts TO oriion_app;
GRANT SELECT, INSERT, UPDATE         ON artifacts.artifacts          TO oriion_app; -- soft-delete only
GRANT SELECT, INSERT                 ON artifacts.artifact_versions  TO oriion_app; -- append-only, immutable
GRANT SELECT, INSERT, UPDATE         ON artifacts.yjs_documents      TO oriion_app;
GRANT SELECT, INSERT, DELETE         ON artifacts.yjs_updates        TO oriion_app; -- DELETE = compaction prune
GRANT SELECT, INSERT                 ON artifacts.yjs_snapshots      TO oriion_app; -- immutable history
GRANT SELECT, INSERT, UPDATE, DELETE ON artifacts.s3_objects         TO oriion_app; -- lifecycle + janitor
GRANT SELECT, INSERT, UPDATE         ON artifacts.cell_storage_usage TO oriion_app;
