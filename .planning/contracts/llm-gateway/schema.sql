-- ============================================================================
-- Bounded context: llm-gateway
-- Purpose: Unified LLM provider routing, BYOK key custody, per-call usage log.
-- ADR refs: ADR-024 (bounded-context contracts), ADR-023 (AI-team runtime),
--           ADR-018 amendment 2026-05-19 (RU-billing currency model).
-- GRILL refs: DECISION-7, P-AUDIT-1 (cost-policy split).
--
-- NAMING (2026-05-19): `organization_id` columns + `app.current_organization_id`
-- RLS GUC renamed to `workspace_id` + `app.current_workspace_id` to match the
-- multitenancy DDL rename (organizations → workspaces).
--
-- CURRENCY (2026-05-19, ADR-018 amendment):
--   * cost_usd      — provider native currency, source-of-truth for provider invoice
--                     reconciliation; kept per original contract.
--   * cost_rub      — customer-facing settlement currency; written atomically with
--                     cost_usd in the same INSERT.
--   * fx_rate_usd_to_rub — pinned at request time; audit-context so historical rows
--                     remain accurate even if FX drifts.
--
-- NOTE on numeric(x,y) cost columns: these are TECHNICAL usage-tracking values
-- (per-request accounting, BYOK quota soft-counter). They are NOT financial
-- policy / spending caps. Cost-policy (per-role monthly cap, Sonnet fallback
-- rules, kill-switch thresholds) lives in
--   `.claude/agents/_shared/cost-budget.yaml`
-- per P-AUDIT-1. Do not encode budget policy in this schema.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- llm_provider_config: registry of supported providers (DeepSeek, YandexGPT,
-- GigaChat, Anthropic, OpenAI, ...). Seeded by ops; not user-writable.
-- ----------------------------------------------------------------------------
CREATE TABLE llm_provider_config (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_slug         text NOT NULL UNIQUE,          -- 'deepseek' | 'yandexgpt' | 'gigachat' | 'anthropic' | 'openai'
    display_name          text NOT NULL,
    default_model         text NOT NULL,
    base_url              text NOT NULL,
    is_byok_supported     boolean NOT NULL DEFAULT true,
    is_active             boolean NOT NULL DEFAULT true,
    supported_features    text[] NOT NULL DEFAULT '{}',  -- subset of {'chat','embeddings','structured_output','tool_use','vision'}
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_provider_config_active
    ON llm_provider_config (is_active) WHERE is_active = true;

COMMENT ON TABLE  llm_provider_config IS 'Static registry of LLM providers. Cost-policy lives in cost-budget.yaml.';
COMMENT ON COLUMN llm_provider_config.supported_features IS 'Capability flags. Used by router to filter providers per request type.';

-- ----------------------------------------------------------------------------
-- byok_keys: per-workspace Bring-Your-Own-Key custody.
-- Raw key never stored — only AES-256-GCM ciphertext with per-workspace KMS DEK.
-- ----------------------------------------------------------------------------
CREATE TABLE byok_keys (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id          uuid NOT NULL REFERENCES multitenancy.workspaces(id) ON DELETE CASCADE,
    provider_slug         text NOT NULL REFERENCES llm_provider_config(provider_slug),
    key_encrypted         bytea NOT NULL,                  -- AES-256-GCM ciphertext (nonce || ciphertext || tag)
    key_fingerprint       text NOT NULL,                   -- sha256(raw_key)[:8] for UI display
    label                 text NOT NULL,                   -- user-given name, e.g. "Marketing team OpenAI"
    monthly_quota_usd     numeric(12,4) NULL,              -- NULL = unlimited; soft-cap (see comment)
    monthly_used_usd      numeric(12,4) NOT NULL DEFAULT 0,
    is_active             boolean NOT NULL DEFAULT true,
    created_by            uuid NOT NULL,                   -- FK to iam.users (cross-context, not enforced)
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),
    revoked_at            timestamptz NULL,
    CONSTRAINT byok_keys_unique_label UNIQUE (workspace_id, provider_slug, label)
);

CREATE INDEX idx_byok_keys_workspace_active
    ON byok_keys (workspace_id) WHERE is_active = true AND revoked_at IS NULL;

COMMENT ON COLUMN byok_keys.monthly_quota_usd IS
    'TECHNICAL soft-quota (provider-side, USD). Best-effort warning at 80%/100%. NOT a policy cap — policy is in cost-budget.yaml (P-AUDIT-1).';
COMMENT ON COLUMN byok_keys.key_encrypted IS
    'AES-256-GCM ciphertext. DEK is per-workspace, wrapped by platform KMS (Wave 0: LocalAESKMS; Wave 1+: Yandex KMS).';

-- RLS: BYOK keys are sensitive — only owner/admin/billing roles within the workspace.
ALTER TABLE byok_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE byok_keys FORCE  ROW LEVEL SECURITY;

CREATE POLICY byok_keys_workspace_isolation ON byok_keys
    USING (workspace_id = current_setting('app.current_workspace_id', true)::uuid);

CREATE POLICY byok_keys_role_restriction ON byok_keys
    FOR ALL
    USING (
        current_setting('app.current_role_slug', true) IN ('owner', 'admin', 'billing')
    );

-- ----------------------------------------------------------------------------
-- llm_usage_log: append-only audit of every LLM call routed by the gateway.
-- Written synchronously BEFORE response returns to caller (invariant #2).
--
-- Currency (2026-05-19 amendment):
--   cost_usd            — provider native (provider invoice reconciliation source)
--   cost_rub            — customer-facing settlement (matches credit_transactions)
--   fx_rate_usd_to_rub  — pinned snapshot at request-time, audit-context
-- ----------------------------------------------------------------------------
CREATE TABLE llm_usage_log (
    id                    bigserial PRIMARY KEY,
    workspace_id          uuid NOT NULL,                   -- FK to multitenancy.workspaces
    cell_id               uuid NOT NULL,                   -- FK to multitenancy.cells
    task_id               uuid NULL,                       -- FK to tasks.tasks (NULL for ad-hoc gateway calls)
    byok_key_id           uuid NULL REFERENCES byok_keys(id), -- NULL if platform-paid key used
    provider_slug         text NOT NULL,
    model_name            text NOT NULL,
    request_id            text NOT NULL,                   -- gateway-generated trace id
    input_tokens          int NOT NULL DEFAULT 0,
    output_tokens         int NOT NULL DEFAULT 0,
    cached_input_tokens   int NOT NULL DEFAULT 0,
    cost_usd              numeric(10,6) NOT NULL DEFAULT 0,
    cost_rub              numeric(12,4) NOT NULL DEFAULT 0,
    fx_rate_usd_to_rub    numeric(10,6) NOT NULL DEFAULT 0,
    latency_ms            int NOT NULL DEFAULT 0,
    status                text NOT NULL CHECK (status IN ('success','error','timeout','rate_limited')),
    error_code            text NULL,
    created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_usage_log_workspace_time ON llm_usage_log (workspace_id, created_at DESC);
CREATE INDEX idx_llm_usage_log_byok_time      ON llm_usage_log (byok_key_id,  created_at DESC) WHERE byok_key_id IS NOT NULL;
CREATE INDEX idx_llm_usage_log_cell_time      ON llm_usage_log (cell_id,      created_at DESC);
CREATE INDEX idx_llm_usage_log_task           ON llm_usage_log (task_id) WHERE task_id IS NOT NULL;
CREATE INDEX idx_llm_usage_log_provider_time  ON llm_usage_log (provider_slug, created_at DESC);

COMMENT ON TABLE  llm_usage_log IS 'Append-only LLM call audit. Cost-policy enforcement is upstream (cost-budget.yaml).';
COMMENT ON COLUMN llm_usage_log.cost_usd IS 'TECHNICAL per-call cost from provider response (native USD). Not a policy threshold.';
COMMENT ON COLUMN llm_usage_log.cost_rub IS 'Customer-facing settlement cost in RUB. cost_rub = cost_usd * fx_rate_usd_to_rub (atomic write).';
COMMENT ON COLUMN llm_usage_log.fx_rate_usd_to_rub IS 'FX snapshot pinned at request-time (Wave 0: env-driven constant; Wave 1+: live FX feed).';

-- RLS: usage log readable to workspace members; sensitive aggregates further filtered in service.
ALTER TABLE llm_usage_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_usage_log FORCE  ROW LEVEL SECURITY;

CREATE POLICY llm_usage_log_workspace_isolation ON llm_usage_log
    USING (workspace_id = current_setting('app.current_workspace_id', true)::uuid);
