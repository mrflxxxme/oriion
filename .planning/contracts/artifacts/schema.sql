-- SKELETON — Wave 1 deliverable (per ADR-024)
-- Detailed DDL deferred to Milestone D, Wave 1 phase
-- Status: structural placeholder for cross-context references
--
-- Context: artifacts
-- Intent: Y.js collaborative documents + S3 binary asset storage
-- Cross-context dependencies:
--   * multitenancy.cells (cell_id is artifact scope)
--   * tasks.task_artifacts (refs yjs_documents.id and s3_assets.id)
--   * rbac.* (per-cell access control)

-- =============================================================================
-- yjs_documents — collaborative document state (Y.js CRDT snapshots)
-- =============================================================================
CREATE TABLE yjs_documents (
    id               uuid        NOT NULL DEFAULT gen_random_uuid(),
    cell_id          uuid        NOT NULL,
    document_type    text        NOT NULL,  -- e.g. 'task-note', 'cell-canvas', 'agent-scratchpad'
    snapshot_jsonb   jsonb       NULL,      -- TODO: replace with binary Y.js update format in Milestone D
    version          int         NOT NULL DEFAULT 1,
    -- TODO: columns в Milestone D Wave 1
    --   yjs_state_vector bytea — Y.js state vector for sync diffs
    --   last_editor_user_id uuid — informational
    --   snapshot_format text — 'jsonb' | 'yjs-binary-v1'
    --   compaction_at timestamptz NULL — when last compacted
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
    -- TODO: FOREIGN KEY (cell_id) REFERENCES multitenancy.cells(id)
);

-- =============================================================================
-- s3_assets — binary asset metadata (object body in S3-compatible storage)
-- =============================================================================
CREATE TABLE s3_assets (
    id                   uuid        NOT NULL DEFAULT gen_random_uuid(),
    cell_id              uuid        NOT NULL,
    s3_bucket            text        NOT NULL,
    s3_key               text        NOT NULL,
    mime_type            text        NULL,
    byte_size            bigint      NULL,
    content_hash_sha256  text        NULL,  -- for dedup + integrity check
    -- TODO: columns в Milestone D Wave 1
    --   uploaded_by_user_id uuid
    --   visibility text — 'cell-private' | 'organization' | 'public-link'
    --   expires_at timestamptz NULL — for ephemeral assets
    --   storage_class text — 'standard' | 'cold'
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE (s3_bucket, s3_key)
    -- TODO: FOREIGN KEY (cell_id) REFERENCES multitenancy.cells(id)
);

-- TODO (Milestone D, Wave 1):
--   * yjs_document_snapshots history table (append-only checkpoint stream)
--   * indexes on (cell_id), (cell_id, document_type) — read-heavy
--   * unique (cell_id, document_type, name) for top-level docs
--   * content_hash_sha256 index for dedup lookups
--   * RLS policies tied to multitenancy + rbac
