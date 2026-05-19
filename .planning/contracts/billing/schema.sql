-- SKELETON — Wave 0 stub (per ADR-024)
-- Detailed DDL будет добавлен в Milestone D / соответствующей Wave-фазе (Wave 2-3)
-- Status: structural placeholder for cross-context references
--
-- ⚠️ NAMING (2026-05-19, per ADR-024 amendment): all references below use the
-- post-rename `workspace_id` / `multitenancy.workspaces` per the canonical
-- multitenancy schema. The full credit_balances/credit_transactions/pricing_table/
-- tariff_plans contract lands in Wave 2-3 (per `contracts/billing/README.md:5-7`).
--
-- Context: billing
-- Intent: credit balances, transactions, pricing table, tariff plans
-- Cross-context dependencies:
--   * multitenancy.workspaces (workspace_id is billing entity)
--   * llm-gateway.llm_usage_log (usage drives credit consumption)
--   * tasks.task_executions (task cost contributes to invoice rollups)
--
-- IMPORTANT: financial numbers (prices, quotas, limits) are NOT hardcoded here
-- (per P-AUDIT-1 in ADR-028 policies registry). AI dev cost caps come from
-- .claude/agents/_shared/cost-budget.yaml; user-facing pricing/quotas come
-- from admin config at runtime.

-- =============================================================================
-- credit_balances — current credit balance per workspace
-- =============================================================================
CREATE TABLE credit_balances (
    id             uuid        NOT NULL DEFAULT gen_random_uuid(),
    workspace_id uuid       NOT NULL,
    -- TODO: columns в Milestone D Phase D.x
    --   balance_amount numeric(18,6) — current credit balance
    --   reserved_amount numeric(18,6) — locked for in-flight tasks
    --   currency_code text — ISO 4217 (или internal credit unit)
    --   last_reconciled_at timestamptz
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
    -- TODO: FOREIGN KEY (workspace_id) REFERENCES multitenancy.workspaces(id)
);

-- =============================================================================
-- credit_transactions — append-only ledger of credit movements
-- =============================================================================
CREATE TABLE credit_transactions (
    id             uuid        NOT NULL DEFAULT gen_random_uuid(),
    workspace_id uuid       NOT NULL,
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
    workspace_id uuid       NULL, -- NULL = global default (workspace-scoped overrides allowed)
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
    workspace_id uuid       NULL, -- NULL = public catalog
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
--   * indexes: (workspace_id), (workspace_id, created_at) on transactions
--   * triggers: maintain credit_balances on transactions insert
--   * constraints: balance_amount >= 0 (or allow negative for overdraft policy)
--   * RLS policies (per ADR-024 multitenancy isolation)
