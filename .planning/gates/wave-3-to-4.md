---
gate: wave-3-to-4
status: PENDING
opened_at: 2026-05-13T12:00:00Z
closed_at: null
founder_signature: null

hard_thresholds:
  paying_customers:
    target: 500
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Active paying subscriptions (not trial, not churned) at gate-evaluation date. Source: billing service. Business growth target per ADR-025, not a cost-policy cap."
  mrr_rub:
    target: 3000000
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Monthly Recurring Revenue in RUB at gate-evaluation date. Recurring subscriptions only; one-time charges, refunds, and trial credits excluded. Source: billing service. Business growth target per ADR-025, not a cost-policy cap."

deliverables:
  - id: D1
    name: "Wave 3 depth/retention features shipped (per .planning/roadmap/wave-3-*)"
    status: pending
    owner: "planner + role-leads"
    notes: "Materialized in roadmap"
  - id: D2
    name: "Customer-success motion operational (playbooks, escalation paths, success-call cadence)"
    status: pending
    owner: "founder + ops"
    notes: "Drives retention and paying_customers growth"
  - id: D3
    name: "Churn cohort dashboard live and reviewed weekly"
    status: pending
    owner: "data + product"
    notes: "Inputs to MRR sustainability"
  - id: D4
    name: "RU payment-method coverage expanded (corporate invoicing, additional providers)"
    status: pending
    owner: "billing-implementer"
    notes: "Removes friction for B2B segment"
  - id: D5
    name: "Multi-tenant analytics shipped (cell-level usage, role-level health)"
    status: pending
    owner: "data + frontend"
    notes: "Supports customer-success motion"
  - id: D6
    name: "Wave 3 cost-budget.yaml review with adjusted caps if needed"
    status: pending
    owner: "founder"
    notes: "Mandatory per cost-budget.yaml review_trigger"

metrics_snapshot:
  snapshot_taken_at: null
  metrics: {}

adr_delta:
  created: []
  revised: []
  superseded: []

risks_delta:
  opened: []
  closed: []
  mitigated: []
  escalated: []

capacity_snapshot:
  ai_team_roles_active: 11
  total_tasks_completed_this_wave: null
  total_cost_usd_this_wave: null
  average_revision_cycles_per_phase: null
  founder_overrides_count: null
---

# Gate: Wave 3 → Wave 4

## Hard thresholds (must-pass)

### `paying_customers >= 500`

Count of active paying subscriptions at gate-evaluation date. Excludes:

- Free trials
- Cancelled / churned subscriptions
- Internal test accounts
- Accounts with refunded most-recent charge

Source: billing service primary query at `SELECT count(*) FROM subscriptions WHERE status='active' AND paid_through > now()`.

### `mrr_rub >= 3_000_000`

Monthly Recurring Revenue in RUB at gate-evaluation date. Computed as:

```
mrr_rub = sum(plan_monthly_price_rub) over active paid subscriptions
```

Annual plans contribute their monthly-equivalent share. One-time charges, setup fees, refunds, and trial credits are excluded. Source: billing service.

### Note on numeric targets (per P-AUDIT-1)

The values 500 customers and 3,000,000 RUB MRR are **business growth targets**, not cost-policy caps or pricing tiers. P-AUDIT-1 restricts hard-coded cost-cap and pricing-tier $-amounts in ADRs and risks documents; business growth targets in RUB or customer counts are a separate category and belong in gate frontmatter where they serve as acceptance criteria.

## Deliverables progress

memory-curator auto-syncs deliverable status. This section is rewritten at gate-evaluation time.

## Retrospective themes

_(Founder fills at evaluation time.)_

## Strategic implications for Wave 4

_(Founder fills: scale/partner features, partner-program design, advanced vertical expansion, multi-region infra prep.)_

## Risk delta narrative

_(Founder fills around populated risks_delta entries.)_

## Cost-budget review

- Budget cap at gate opening: _per `.claude/agents/_shared/cost-budget.yaml` as adjusted by Wave 2 → 3 review_.
- Actual spend this wave: _to be measured via Langfuse aggregation_.
- Adjustment proposed for Wave 4: _to be decided based on unit economics (cost per paying customer) and per-month cap utilization_.
- Founder decision: _pending_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
