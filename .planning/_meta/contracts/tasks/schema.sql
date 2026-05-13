-- ============================================================================
-- Bounded context: tasks
-- Purpose: A `task` is one agent-team execution within a cell. Steps are
--          ordered atomic operations (LLM call, tool use, user input wait,
--          branch/merge). Artifacts are produced outputs (inline, S3, Yjs).
-- ADR refs: ADR-024 (bounded-context contracts), ADR-023 (AI-team runtime).
-- GRILL refs: DECISION-7.
--
-- Naming: column name is `agent_archetype_id` (canonical, ADR-024 §2 / P-AUDIT-2).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- tasks: top-level execution unit. A task has a status lifecycle and aggregates
-- cost/tokens across its steps.
-- ----------------------------------------------------------------------------
CREATE TABLE tasks (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id                  uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    agent_instance_id        uuid NULL REFERENCES agents.agent_instances(id),  -- NULL = ad-hoc run, no preset
    team_preset_id           uuid NULL,                                         -- FK to agents.team_presets(id) (cross-context)
    initiated_by_user_id     uuid NOT NULL,                                     -- FK to iam.users (cross-context)
    title                    text NOT NULL,
    description              text NOT NULL DEFAULT '',
    input_jsonb              jsonb NOT NULL DEFAULT '{}'::jsonb,
    status                   text NOT NULL DEFAULT 'queued' CHECK (status IN
                                ('queued','running','waiting_input','succeeded','failed','cancelled','timed_out')),
    priority                 smallint NOT NULL DEFAULT 5,                       -- 1 (highest) .. 9 (lowest)
    started_at               timestamptz NULL,
    completed_at             timestamptz NULL,
    total_cost_usd           numeric(10,6) NOT NULL DEFAULT 0,                  -- TECHNICAL aggregate; not a budget cap
    total_input_tokens       bigint NOT NULL DEFAULT 0,
    total_output_tokens      bigint NOT NULL DEFAULT 0,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_cell_status_time
    ON tasks (cell_id, status, created_at DESC);

CREATE INDEX idx_tasks_instance_completed
    ON tasks (agent_instance_id, completed_at DESC NULLS LAST);

CREATE INDEX idx_tasks_status_priority
    ON tasks (status, priority, created_at) WHERE status IN ('queued','running');

COMMENT ON TABLE  tasks IS
    'Top-level execution unit (one agent-team run inside a cell). Domain concept distinct from .planning/ phases.';
COMMENT ON COLUMN tasks.total_cost_usd IS
    'TECHNICAL aggregate of step costs. Policy/caps live in `.claude/agents/_shared/cost-budget.yaml`.';

-- RLS: visible to cell members.
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tasks_cell_isolation ON tasks
    USING (cell_id = current_setting('app.current_cell_id', true)::uuid);

-- ----------------------------------------------------------------------------
-- task_steps: ordered, atomic operations within a task. Denormalises
-- `agent_archetype_id` for post-hoc analysis (even if archetype version
-- evolves later, step records remain truthful about who-ran-what).
-- ----------------------------------------------------------------------------
CREATE TABLE task_steps (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id              uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_index           int  NOT NULL,
    -- Denormalised snapshot. Canonical column name (ADR-024 §2 / P-AUDIT-2).
    agent_archetype_id   uuid NOT NULL REFERENCES agents.agent_archetypes(id),
    step_type            text NOT NULL CHECK (step_type IN
                            ('llm_call','tool_use','user_input','wait','branch','merge')),
    input_jsonb          jsonb NOT NULL DEFAULT '{}'::jsonb,
    output_jsonb         jsonb NOT NULL DEFAULT '{}'::jsonb,
    status               text NOT NULL DEFAULT 'queued' CHECK (status IN
                            ('queued','running','waiting_input','succeeded','failed','skipped','cancelled')),
    started_at           timestamptz NULL,
    completed_at         timestamptz NULL,
    cost_usd             numeric(10,6) NOT NULL DEFAULT 0,
    error_jsonb          jsonb NULL,
    CONSTRAINT task_steps_unique_index UNIQUE (task_id, step_index)
);

CREATE INDEX idx_task_steps_task_status
    ON task_steps (task_id, status, step_index);

CREATE INDEX idx_task_steps_archetype_time
    ON task_steps (agent_archetype_id, completed_at DESC) WHERE completed_at IS NOT NULL;

COMMENT ON COLUMN task_steps.agent_archetype_id IS
    'Denormalised snapshot of the archetype that executed this step. Survives archetype version bumps. Canonical FK name (ADR-024 §2).';

-- ----------------------------------------------------------------------------
-- task_artifacts: outputs produced by a task or step. Storage choice depends
-- on size and type (invariant #4).
-- ----------------------------------------------------------------------------
CREATE TABLE task_artifacts (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id              uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_id              uuid NULL REFERENCES task_steps(id) ON DELETE SET NULL,
    artifact_type        text NOT NULL CHECK (artifact_type IN
                            ('text','image','file','structured_data','code')),
    storage_kind         text NOT NULL CHECK (storage_kind IN
                            ('inline','s3','yjs_document')),
    content_inline       jsonb NULL,                       -- non-null IFF storage_kind = 'inline'
    s3_key               text  NULL,                       -- non-null IFF storage_kind = 's3'
    yjs_document_id      uuid  NULL,                       -- FK to artifacts.yjs_documents (Wave 1)
    mime_type            text NOT NULL,
    byte_size            bigint NOT NULL DEFAULT 0,
    content_hash_sha256  text NOT NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT task_artifacts_storage_xor CHECK (
        (storage_kind = 'inline'       AND content_inline   IS NOT NULL AND s3_key IS NULL     AND yjs_document_id IS NULL)
     OR (storage_kind = 's3'           AND s3_key           IS NOT NULL AND content_inline IS NULL AND yjs_document_id IS NULL)
     OR (storage_kind = 'yjs_document' AND yjs_document_id IS NOT NULL AND content_inline IS NULL AND s3_key IS NULL)
    )
);

CREATE INDEX idx_task_artifacts_task        ON task_artifacts (task_id, created_at DESC);
CREATE INDEX idx_task_artifacts_step        ON task_artifacts (step_id) WHERE step_id IS NOT NULL;
CREATE INDEX idx_task_artifacts_hash        ON task_artifacts (content_hash_sha256);

COMMENT ON TABLE task_artifacts IS
    'Outputs of a task/step. Retention policy is per-cell (Wave 1). Failed tasks may retain artifacts for forensic review.';

-- RLS on steps and artifacts: visible if parent task is visible (relies on
-- service layer joining through tasks for the cell_id check).
ALTER TABLE task_steps     ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_artifacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_steps_via_task ON task_steps
    USING (EXISTS (
        SELECT 1 FROM tasks t
        WHERE t.id = task_steps.task_id
          AND t.cell_id = current_setting('app.current_cell_id', true)::uuid
    ));

CREATE POLICY task_artifacts_via_task ON task_artifacts
    USING (EXISTS (
        SELECT 1 FROM tasks t
        WHERE t.id = task_artifacts.task_id
          AND t.cell_id = current_setting('app.current_cell_id', true)::uuid
    ));
