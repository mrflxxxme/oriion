---
gate: wave-4-to-5
status: PENDING
opened_at: 2026-05-13T12:00:00Z
closed_at: null
founder_signature: null

hard_thresholds:
  paying_customers:
    target: 2000
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Active paying subscriptions (not trial, not churned) at gate-evaluation date. Source: billing service. Business growth target per ADR-025, not a cost-policy cap."
  mrr_rub:
    target: 15000000
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Monthly Recurring Revenue in RUB at gate-evaluation date. Recurring subscriptions only; one-time charges, refunds, and trial credits excluded. Source: billing service. Business growth target per ADR-025, not a cost-policy cap."

deliverables:
  - id: D1
    name: "Wave 4 scale/partner features shipped (per .planning/roadmap/wave-4-*)"
    status: pending
    owner: "planner + role-leads"
    notes: "Materialized in roadmap"
  - id: D2
    name: "Partner-program operational (referral mechanics, partner dashboards, payout flow)"
    status: pending
    owner: "founder + ops + billing-implementer"
    notes: "Channel for next-wave growth"
  - id: D3
    name: "Advanced verticals shipped beyond the Wave 1 starter set"
    status: pending
    owner: "vertical-prompt-author + evaluator"
    notes: "Per ADR-026 expansion roadmap; each new vertical passes Level B + Level C gates"
  - id: D4
    name: "Multi-region infrastructure deployed (read-replica or active-active per ADR-001 evolution)"
    status: pending
    owner: "architect + devops"
    notes: "Reduces latency and de-risks single-region failure"
  - id: D5
    name: "Enterprise SSO shipped (SAML / OIDC integration per ADR-007 evolution)"
    status: pending
    owner: "iam-implementer"
    notes: "Unblocks enterprise segment"
  - id: D6
    name: "Wave 4 cost-budget.yaml review with adjusted caps if needed"
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

# Gate: Wave 4 → Wave 5

## Hard thresholds (must-pass)

### `paying_customers >= 2000`

Count of active paying subscriptions at gate-evaluation date. Exclusions and source query same as `wave-3-to-4` gate.

### `mrr_rub >= 15_000_000`

Monthly Recurring Revenue in RUB at gate-evaluation date. Computation and source same as `wave-3-to-4` gate.

### Note on numeric targets (per P-AUDIT-1)

The values 2000 customers and 15,000,000 RUB MRR are **business growth targets**, not cost-policy caps or pricing tiers. P-AUDIT-1 restricts hard-coded cost-cap and pricing-tier $-amounts in ADRs and risks documents; business growth targets in RUB or customer counts are a separate category and belong in gate frontmatter where they serve as acceptance criteria.

## Deliverables progress

memory-curator auto-syncs deliverable status. This section is rewritten at gate-evaluation time.

## Retrospective themes

_(Founder fills at evaluation time.)_

## Strategic implications for Wave 5

_(Founder fills: platformization, ecosystem APIs, international expansion candidates, organizational scaling, expected ADR creations.)_

## Risk delta narrative

_(Founder fills around populated risks_delta entries.)_

## Cost-budget review

- Budget cap at gate opening: _per `.claude/agents/_shared/cost-budget.yaml` as adjusted by Wave 3 → 4 review_.
- Actual spend this wave: _to be measured via Langfuse aggregation_.
- Adjustment proposed for Wave 5: _to be decided based on unit economics at scale and per-month cap utilization_.
- Founder decision: _pending_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
