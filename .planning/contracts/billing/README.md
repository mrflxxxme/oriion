<!-- SKELETON — Wave 0 stub (per ADR-024). Draft quality README; SQL/YAML files are placeholders. -->

# Bounded Context: `billing`

> **Status:** SKELETON (Wave 0 stub per ADR-024). Real DDL/API/events deferred to Milestone D, Wave 2-3.

## Purpose

The `billing` context owns the **financial lifecycle** of an Oriion organization:
issuing invoices, tracking credit balances, recording consumption transactions,
managing tariff plans, and integrating with payment providers.

It is intentionally isolated from operational contexts (`tasks`, `agents`, `llm-gateway`) —
billing is a downstream consumer of usage events, not a participant in execution paths.

## Ubiquitous Language (stub)

| Term            | Meaning                                                                            |
|-----------------|------------------------------------------------------------------------------------|
| **Tariff**      | Subscription plan (e.g. `free`, `starter`, `pro`) bundling allowances + features.  |
| **Credit**      | Internal unit of consumption; mapped to currency via `pricing_table`.              |
| **Invoice**     | Periodic statement of charges issued to an organization.                           |
| **Subscription**| Active tariff binding for an organization (one active subscription per org).       |
| **Transaction** | Atomic credit movement (topup, consumption, refund, adjustment). Append-only.      |
| **Balance**     | Aggregate of transactions; cached in `credit_balances` for read performance.       |

## Invariants (placeholder — TODO in Milestone D)

- TODO: `credit_balances.balance_amount` derived as SUM(transactions.amount) per organization.
- TODO: `credit_transactions` is append-only (no UPDATE/DELETE outside corrections).
- TODO: An organization has at most one active subscription at any time.
- TODO: Consumption events must reference a valid `pricing_table` row effective at event time.
- TODO: Refunds reference the originating consumption transaction.

## Cross-Context Dependencies

- **multitenancy** — every billing row is scoped to `organization_id` (the billing entity).
- **llm-gateway** — `llm_usage_log` rows are the primary driver of `credit.consumed` events.
- **tasks** — task execution cost (aggregating LLM + MCP + storage) is rolled up into invoice line items.
- **iam** — billing admin permission scope (TODO: which RBAC role gates `/billing/*` access).
- **mcp** — per-invocation MCP tool usage contributes to consumption (Wave 2+).

## Why SKELETON (not full Wave 0)

Billing is **not on the critical path** for Wave 0 internal demo:

1. Wave 0 traffic is internal/seed-only — no real payment flows.
2. Pricing model itself is still under discussion (per-token vs per-task vs hybrid).
3. Real implementation lands in **Wave 2-3**, once public traffic + payment provider integration are scoped.

In the interim, this skeleton exists to:

- Reserve the schema namespace and prevent naming collisions.
- Give cross-context references (e.g. `multitenancy.organizations`) a clear target.
- Document the intent so subsequent ADRs can refine without renaming.

## Cost Policy Note (per P-AUDIT-1)

Financial numbers (prices, allowances, quotas, overage rates) are **never hardcoded**
in this context's schema or code. They flow from:

- `.planning/_meta/cost-budget.yaml` — engineering-level budget envelopes.
- Admin config (TODO: surface) — runtime pricing rules editable by ops.
- `pricing_table` rows — versioned, effective-dated, per-organization overrides.

## ADR References

- **ADR-024** — Bounded Context Contracts (this context schema, §1).
- **R-31** (in risk register) — cost-policy bound to billing flow; no $-numbers in code.
- TODO: future ADR on payment-provider choice (Wave 2-3).

## Open Questions (defer to Milestone D)

- Credit unit semantics: 1 credit == 1 token? per-vendor normalization?
- Refund window and dispute workflow.
- Multi-currency support (yes/no at MVP).
- Tax handling (jurisdictional VAT, reverse-charge).
- Dunning / collection workflow on negative balance.
