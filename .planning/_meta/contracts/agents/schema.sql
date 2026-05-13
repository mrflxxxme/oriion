-- ============================================================================
-- Bounded context: agents
-- Purpose: Bridge between authoring layer (`_meta/verticals/<slug>/prompts/*.md`)
--          and runtime cell-level AI agent instances.
-- ADR refs: ADR-024 (bounded-context contracts), ADR-026 (vertical-expertise),
--           ADR-010 (role-versioning).
-- GRILL refs: DECISION-7, DECISION-11 (prompt status), P-AUDIT-2 (naming).
--
-- CRITICAL NAMING (per ADR-024 §2 and P-AUDIT-2 enforcement):
--   * `agent_archetypes`   — vertical-level AI personas. Authoritative table.
--                            Deprecated alias: `roles_agent` (DO NOT USE).
--   * `agent_archetype_id` — FK column name everywhere. Deprecated aliases:
--                            `ui_sprite_archetype`, `sprite_id` (DO NOT USE).
--   * `system_roles`       — system-level RBAC roles (Owner/Admin/Editor).
--                            Lives in the `rbac` bounded context — DO NOT
--                            confuse with `agent_archetypes`.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- agent_archetypes: vertical-level AI personas, e.g. wb-coordinator,
-- wb-researcher, wb-listing-writer. Each row references a prompt file in
-- `_meta/verticals/<vertical_slug>/prompts/<slug>.md` and pins its version.
-- ----------------------------------------------------------------------------
CREATE TABLE agent_archetypes (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                  text NOT NULL,                   -- e.g. 'wb-coordinator'
    vertical_slug         text NOT NULL,                   -- references `_meta/verticals/<slug>/`
    display_name          text NOT NULL,
    role_category         text NOT NULL CHECK (role_category IN
                            ('coordinator','researcher','writer','analyzer','validator','communicator')),
    prompt_version        text NOT NULL,                   -- semver from prompt frontmatter, e.g. '0.1.0'
    model_provider_slug   text NOT NULL,                   -- FK to llm-gateway.llm_provider_config.provider_slug (cross-context)
    model_name            text NOT NULL,
    model_fallback        text NULL,                       -- e.g. Sonnet fallback per cost-budget.yaml
    tools_allowed         text[] NOT NULL DEFAULT '{}',    -- tool slugs whitelisted for this archetype
    is_active             boolean NOT NULL DEFAULT true,
    status                text NOT NULL DEFAULT 'draft' CHECK (status IN
                            ('draft','reviewed','promoted','locked')),
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),
    deprecated_at         timestamptz NULL,
    CONSTRAINT agent_archetypes_unique UNIQUE (vertical_slug, slug, prompt_version)
);

CREATE INDEX idx_agent_archetypes_vertical_active
    ON agent_archetypes (vertical_slug)
    WHERE is_active = true AND deprecated_at IS NULL;

CREATE INDEX idx_agent_archetypes_status
    ON agent_archetypes (status, vertical_slug);

COMMENT ON TABLE  agent_archetypes IS
    'Vertical-level AI personas. Authoritative table — replaces deprecated `roles_agent`. See ADR-024 §2.';
COMMENT ON COLUMN agent_archetypes.prompt_version IS
    'Must equal the `version:` field in frontmatter of `_meta/verticals/<vertical_slug>/prompts/<slug>.md`.';
COMMENT ON COLUMN agent_archetypes.status IS
    'Lifecycle per DECISION-11. Only `locked` archetypes are usable in production cell-instances.';

-- ----------------------------------------------------------------------------
-- team_presets: opinionated archetype compositions for fast cell bootstrap.
-- E.g. "WB-Starter" = {wb-coordinator, wb-researcher, wb-listing-writer}.
-- ----------------------------------------------------------------------------
CREATE TABLE team_presets (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vertical_slug               text NOT NULL,
    slug                        text NOT NULL,
    display_name                text NOT NULL,
    description                 text NOT NULL DEFAULT '',
    archetype_ids               uuid[] NOT NULL,         -- ordered list of agent_archetypes.id
    default_workflow_dag_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at                  timestamptz NOT NULL DEFAULT now(),
    updated_at                  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT team_presets_unique UNIQUE (vertical_slug, slug)
);

COMMENT ON COLUMN team_presets.archetype_ids IS
    'Ordered FK array to agent_archetypes.id. Application enforces all locked + same vertical.';

-- ----------------------------------------------------------------------------
-- agent_instances: per-cell instantiations of an archetype. Founder can rename
-- and override settings without forking the archetype.
-- ----------------------------------------------------------------------------
CREATE TABLE agent_instances (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id                  uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
    -- Column name MUST be `agent_archetype_id` (ADR-024 §2, P-AUDIT-2).
    -- Deprecated aliases `ui_sprite_archetype` / `sprite_id` are forbidden.
    agent_archetype_id       uuid NOT NULL REFERENCES agent_archetypes(id),
    custom_name              text NULL,                  -- cell-level rename (e.g. "Marketing Anna")
    custom_settings_jsonb    jsonb NOT NULL DEFAULT '{}'::jsonb,
    total_tasks_completed    int NOT NULL DEFAULT 0,
    last_used_at             timestamptz NULL,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now(),
    archived_at              timestamptz NULL
);

CREATE INDEX idx_agent_instances_cell_active
    ON agent_instances (cell_id)
    WHERE archived_at IS NULL;

CREATE INDEX idx_agent_instances_archetype
    ON agent_instances (agent_archetype_id);

COMMENT ON COLUMN agent_instances.agent_archetype_id IS
    'FK to agent_archetypes.id. Canonical column name per ADR-024 §2 / P-AUDIT-2. Deprecated aliases forbidden.';

-- RLS: visible to cell members only.
ALTER TABLE agent_instances ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_instances_cell_isolation ON agent_instances
    USING (cell_id = current_setting('app.current_cell_id', true)::uuid);
