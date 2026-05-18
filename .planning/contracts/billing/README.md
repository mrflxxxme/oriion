<!-- SKELETON — Wave 0 stub (per ADR-024). Wave 0 inline contract for `credit_transactions` only; full DDL/API/events deferred to Milestone D, Wave 2-3. -->

# Bounded Context: `billing`

> **Status:** SKELETON (Wave 0 stub per ADR-024). Real DDL/API/events deferred to Milestone D, Wave 2-3.
>
> **Wave 0 inline contract (2026-05-19):** `billing.credit_transactions` SKELETON DDL ships with Phase 00.4 — required for LLM cost ledger (RU-billing). Real `credit_balances`, `pricing_table`, `tariff_plans`, `subscriptions`, `invoices` land in Wave 2-3 when monetization opens.

## Purpose

The `billing` context owns the **financial lifecycle** of an Oriion workspace:
issuing invoices, tracking credit balances, recording consumption transactions,
managing tariff plans, and integrating with payment providers.

It is intentionally isolated from operational contexts (`tasks`, `agents`, `llm-gateway`) —
billing is a downstream consumer of usage events, not a participant in execution paths.

## Naming (2026-05-19)

> Per the multitenancy DDL rename, the billing tenant identifier is
> **`workspace_id`** (was `organization_id`). Wave 0 `credit_transactions`
> rows carry `cell_id` (per-cell credit accounting per ADR-009); workspace
> aggregation happens via join with `multitenancy.cells.workspace_id`.

## Currency model — RU-first (Wave 0 inline)

> Customer-facing settlement is **RUB**. Provider reconciliation in USD via
> `llm_gateway.llm_usage_log.cost_usd`. See `contracts/llm-gateway/README.md`
> Currency model section + ADR-018 amendment 2026-05-19.

```sql
-- Wave 0 inline SKELETON — backend/migrations/versions/billing/0001_credit_transactions_skeleton.py
CREATE TABLE billing.credit_transactions (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id                uuid NOT NULL,
    workspace_id           uuid NOT NULL,
    user_id                uuid NULL,
    task_id                uuid NULL,
    transaction_type       text NOT NULL CHECK (transaction_type IN ('debit', 'credit', 'refund', 'trial_grant')),
    amount_rub             numeric(12,4) NOT NULL,
    amount_credits         numeric(12,4) NOT NULL,
    balance_after_credits  numeric(12,4) NOT NULL,
    fx_rate_usd_to_rub     numeric(10,6) NULL,
    provider               text NULL,
    model                  text NULL,
    tokens_input           int NOT NULL DEFAULT 0,
    tokens_output          int NOT NULL DEFAULT 0,
    payload                jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at             timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_credit_tx_cell_created      ON billing.credit_transactions (cell_id, created_at DESC);
CREATE INDEX ix_credit_tx_workspace_created ON billing.credit_transactions (workspace_id, created_at DESC);
CREATE INDEX ix_credit_tx_task              ON billing.credit_transactions (task_id) WHERE task_id IS NOT NULL;

-- RLS — cell isolation per ADR-009 (Phase 00.3 pattern)
ALTER TABLE billing.credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.credit_transactions FORCE  ROW LEVEL SECURITY;
CREATE POLICY ct_cell_isolation ON billing.credit_transactions
    USING (cell_id = current_setting('app.current_cell_id', true)::uuid);
```

## Ubiquitous Language (stub)

| Term            | Meaning                                                                            |
|-----------------|------------------------------------------------------------------------------------|
| **Tariff**      | Subscription plan (e.g. `free`, `starter`, `pro`) bundling allowances + features.  |
| **Credit**      | Internal unit of consumption; 1 credit = 1 RUB (Wave 0); mapped via `pricing_table` Wave 2+. |
| **Invoice**     | Periodic statement of charges issued to a workspace.                               |
| **Subscription**| Active tariff binding for a workspace (one active subscription per workspace).     |
| **Transaction** | Atomic credit movement (topup, consumption, refund, adjustment). Append-only.      |
| **Balance**     | Aggregate of transactions; cached in `credit_balances` for read performance.       |

## Invariants (Wave 0 inline + placeholder Milestone D)

- **Wave 0:** `credit_transactions` is append-only (no UPDATE/DELETE outside corrections). Enforced application-side.
- **Wave 0:** `amount_rub = amount_credits × 1.0` (1 credit = 1 RUB). Wave 2+ introduces conversion via `pricing_table`.
- **Wave 0:** Each LLM-driven debit row references the originating `llm_usage_log` row via `payload.llm_usage_log_id`.
- TODO Milestone D: `credit_balances.balance_amount` derived as SUM(transactions.amount) per workspace.
- TODO Milestone D: A workspace has at most one active subscription at any time.
- TODO Milestone D: Consumption events must reference a valid `pricing_table` row effective at event time.
- TODO Milestone D: Refunds reference the originating consumption transaction.

## Cross-Context Dependencies

- **multitenancy** — every billing row is scoped to `workspace_id` (the billing entity) and `cell_id` (consumption attribution).
- **llm-gateway** — `llm_usage_log` rows drive `credit.consumed` events; atomic write contract in invariant #7 of llm-gateway README.
- **tasks** — task execution cost (aggregating LLM + MCP + storage) is rolled up into invoice line items.
- **iam** — billing admin permission scope (`billing.view` / `billing.manage` — RBAC roles `owner`, `billing`).
- **mcp** — per-invocation MCP tool usage contributes to consumption (Wave 2+).

## Why SKELETON (not full Wave 0)

Billing is **not on the critical path** for Wave 0 internal demo:

1. Wave 0 traffic is internal/seed-only — no real payment flows.
2. Pricing model itself is still under discussion (per-token vs per-task vs hybrid).
3. Real implementation lands in **Wave 2-3**, once public traffic + payment provider integration are scoped.

In the interim, this skeleton + the inline `credit_transactions` DDL exist to:

- Reserve the schema namespace and prevent naming collisions.
- Give cross-context references (e.g. `llm_gateway.llm_usage_log → credit_transactions`) a concrete target.
- Document the intent so subsequent ADRs can refine without renaming.

## Cost Policy Note (per P-AUDIT-1)

Financial numbers (prices, allowances, quotas, overage rates) are **never hardcoded**
in this context's schema or code. They flow from:

- `.claude/agents/_shared/cost-budget.yaml` — engineering-level budget envelopes.
- Admin config (TODO: surface) — runtime pricing rules editable by ops.
- `pricing_table` rows — versioned, effective-dated, per-workspace overrides (Wave 2+).
- `llm_gateway.llm_usage_log.fx_rate_usd_to_rub` — pinned FX snapshot per request.

## ADR References

- **ADR-024** — Bounded Context Contracts (this context schema, §1).
- **ADR-018** amendment 2026-05-19 — RU-currency model.
- **R-31** (in risk register) — cost-policy bound to billing flow; no $-numbers in code.
- TODO: future ADR on payment-provider choice (Wave 2-3, ЮKassa via `TBD_YUKASSA_SHOP_ID`).

## Open Questions (defer to Milestone D)

- Credit unit semantics: keep 1 credit = 1 RUB or floating exchange?
- Refund window and dispute workflow.
- Multi-currency support (yes/no at MVP — currently no, RUB-only).
- Tax handling (jurisdictional VAT, reverse-charge).
- Dunning / collection workflow on negative balance.
