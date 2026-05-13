-- SKELETON — Wave 0 stub (per ADR-024)
-- Detailed DDL будет добавлен в Milestone D / соответствующей Wave-фазе (Wave 2-3)
-- Status: structural placeholder for cross-context references
--
-- Context: billing
-- Intent: credit balances, transactions, pricing table, tariff plans
-- Cross-context dependencies:
--   * multitenancy.organizations (organization_id is billing entity)
--   * llm-gateway.llm_usage_log (usage drives credit consumption)
--   * tasks.task_executions (task cost contributes to invoice rollups)
--
-- IMPORTANT: financial numbers (prices, quotas, limits) are NOT hardcoded here
-- (per P-AUDIT-1 in GRILL-DECISIONS-ORIION). Values come from admin config +
-- .planning/_meta/cost-budget.yaml at runtime.

-- =============================================================================
-- credit_balances — current credit balance per organization
-- =============================================================================
CREATE TABLE credit_balances (
    id             uuid        NOT NULL DEFAULT gen_random_uuid(),
    organization_id uuid       NOT NULL,
    -- TODO: columns в Milestone D Phase D.x
    --   balance_amount numeric(18,6) — current credit balance
    --   reserved_amount numeric(18,6) — locked for in-flight tasks
    --   currency_code text — ISO 4217 (или internal credit unit)
    --   last_reconciled_at timestamptz
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
    -- TODO: FOREIGN KEY (organization_id) REFERENCES multitenancy.organizations(id)
);

-- =============================================================================
-- credit_transactions — append-only ledger of credit movements
-- =============================================================================
CREATE TABLE credit_transactions (
    id             uuid        NOT NULL DEFAULT gen_random_uuid(),
    organization_id uuid       NOT NULL,
    -- TODO: columns в Milestone D Phase D.x
    --   transaction_type text — 'topup' | 'consumption' | 'refund' | 'adjustment'
    --   amount numeric(18,6) — signed (+ topup, − consumption)
    --   source_ref_type text — 'invoice' | 'task_execution' | 'manual'
    --   source_ref_id uuid — polymorphic FK
    --   description text
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

-- =============================================================================
-- pricing_table — current pricing rules (lookup table, versioned)
-- =============================================================================
CREATE TABLE pricing_table (
    id             uuid        NOT NULL DEFAULT gen_random_uuid(),
    organization_id uuid       NULL, -- NULL = global default
    -- TODO: columns в Milestone D Phase D.x
    --   sku text — 'llm.input_token' | 'llm.output_token' | 'mcp.invocation' | ...
    --   unit text — 'token' | 'invocation' | 'second'
    --   unit_price numeric(18,8) — price per unit in credit
    --   effective_from timestamptz
    --   effective_to timestamptz NULL
    --   version int
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

-- =============================================================================
-- tariff_plans — subscription tier definitions
-- =============================================================================
CREATE TABLE tariff_plans (
    id             uuid        NOT NULL DEFAULT gen_random_uuid(),
    organization_id uuid       NULL, -- NULL = public catalog
    -- TODO: columns в Milestone D Phase D.x
    --   plan_code text — 'free' | 'starter' | 'pro' | 'enterprise'
    --   monthly_credit_allowance numeric(18,6)
    --   feature_flags jsonb — entitlements
    --   billing_period text — 'monthly' | 'annual'
    --   is_active boolean
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

-- TODO (Milestone D):
--   * indexes: (organization_id), (organization_id, created_at) on transactions
--   * triggers: maintain credit_balances on transactions insert
--   * constraints: balance_amount >= 0 (or allow negative for overdraft policy)
--   * RLS policies (per ADR-024 multitenancy isolation)
