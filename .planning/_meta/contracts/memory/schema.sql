-- SKELETON — Wave 1 deliverable (per ADR-024)
-- Detailed DDL deferred to Milestone D, Wave 1 phase
-- Status: structural placeholder for cross-context references
--
-- Context: memory
-- Intent: cell-level long-term memory + role-level agent memory.
--         Vector embeddings (ONNX 384-dim) via AgentDB MCP per ADR-023 §6-7.
-- Cross-context dependencies:
--   * multitenancy.cells (cell_id is memory scope for cell_memory)
--   * agents.agent_archetypes (agent_archetype_id is scope for role_memory)
--   * AgentDB MCP runtime (HNSW vector index, all-MiniLM-L6-v2 384-dim, per ADR-023)
--
-- NAMING COMPLIANCE (per GRILL P-AUDIT-2):
--   * Always use `agent_archetype_id` (NEVER deprecated `ui_sprite_archetype`).
--   * FK targets `agents.agent_archetypes` (NEVER `roles_agent`).
--
-- DEPENDENCY: requires `pgvector` Postgres extension.
--   CREATE EXTENSION IF NOT EXISTS vector;
--
-- DUAL-STORE NOTE: this schema is the control-plane registry. Actual semantic
-- search at runtime is served by AgentDB MCP (HNSW index, ONNX 384-dim
-- embeddings) per ADR-023 §6-7. Postgres rows mirror keys + metadata; the
-- embedding column here exists for backup / rebuild / consistency check.

-- =============================================================================
-- cell_memory — workspace-scoped long-term memory (facts, decisions, context)
-- =============================================================================
CREATE TABLE cell_memory (
    id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    cell_id         uuid        NOT NULL,
    namespace       text        NOT NULL,                      -- partition within a cell
    key             text        NOT NULL,                      -- stable identifier within namespace
    value_jsonb     jsonb       NULL,                          -- structured value payload
    embedding       vector(384) NULL,                          -- ONNX all-MiniLM-L6-v2 (per ADR-023)
    ttl_seconds     int         NULL,                          -- optional expiry; NULL = persistent
    -- TODO: columns в Milestone D Wave 1
    --   source_ref_type text — 'task' | 'manual' | 'distilled'
    --   source_ref_id uuid — origin of the memory entry
    --   confidence_score real — for distilled / inferred memories
    --   last_accessed_at timestamptz — for LRU pruning
    --   access_count int — usage signal
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE (cell_id, namespace, key)
    -- TODO: FOREIGN KEY (cell_id) REFERENCES multitenancy.cells(id)
);

-- =============================================================================
-- role_memory — agent-archetype-scoped global patterns (cross-cell learnings)
-- =============================================================================
CREATE TABLE role_memory (
    id                   uuid        NOT NULL DEFAULT gen_random_uuid(),
    agent_archetype_id   uuid        NOT NULL,                 -- per P-AUDIT-2 naming
    namespace            text        NOT NULL,
    key                  text        NOT NULL,
    value_jsonb          jsonb       NULL,
    embedding            vector(384) NULL,                     -- ONNX 384-dim per ADR-023
    -- TODO: columns в Milestone D Wave 1
    --   pattern_type text — 'success' | 'failure' | 'preference'
    --   reward_signal real — ReasoningBank-style score
    --   sample_count int — how many trajectories backed this pattern
    --   ewc_lambda real — EWC++ importance for catastrophic-forgetting prevention
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE (agent_archetype_id, namespace, key)
    -- TODO: FOREIGN KEY (agent_archetype_id) REFERENCES agents.agent_archetypes(id)
);

-- =============================================================================
-- embedding_index_metadata — registry of embedding models + index configs in use
-- =============================================================================
CREATE TABLE embedding_index_metadata (
    id               uuid        NOT NULL DEFAULT gen_random_uuid(),
    model_name       text        NOT NULL,           -- e.g. 'all-MiniLM-L6-v2'
    dimension        int         NOT NULL,           -- e.g. 384 (per ADR-023)
    distance_metric  text        NOT NULL,           -- 'cosine' | 'l2' | 'inner_product'
    -- TODO: columns в Milestone D Wave 1
    --   index_type text — 'hnsw' | 'diskann' | 'flat'
    --   index_params_jsonb — m, ef_construction, ef_search
    --   model_provenance text — onnx file hash, source repo
    --   is_active boolean
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    UNIQUE (model_name, dimension, distance_metric)
);

-- TODO (Milestone D, Wave 1):
--   * HNSW indexes on cell_memory.embedding and role_memory.embedding
--   * partial indexes WHERE ttl_seconds IS NOT NULL for expiry sweeper
--   * RLS policies tied to multitenancy.cells and agents.agent_archetypes
--   * trigger: on update, refresh embedding via AgentDB MCP if value_jsonb changed
