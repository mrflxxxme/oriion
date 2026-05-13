---
gate: wave-2-to-3
status: PENDING
opened_at: 2026-05-13T12:00:00Z
closed_at: null
founder_signature: null

hard_thresholds:
  weekly_registrations:
    target: 100
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "New cells registered per week, computed as a 4-week rolling average over the last completed 4 weeks of Wave 2. Source: product analytics dashboard."
  ttfv_minutes:
    target: 3
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Median time-to-first-value (registration completed -> first task completed and approved) measured across new cells registered in the last 30 days. Source: product analytics dashboard. Target = 3 minutes or less (lower is better)."
  conversion:
    target: 0.05
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Registration-to-paid conversion within a 4-week window. Cohort: cells registered 4+ weeks before gate evaluation. Computed as paid(cohort) / registered(cohort)."

deliverables:
  - id: D1
    name: "Wave 2 public-beta features shipped (per .planning/roadmap/wave-2-*)"
    status: pending
    owner: "planner + role-leads"
    notes: "Materialized in roadmap"
  - id: D2
    name: "Payment flow live with RU payment methods (CloudPayments / YooMoney coverage)"
    status: pending
    owner: "billing-implementer"
    notes: "Per ADR-008 credits-billing"
  - id: D3
    name: "Onboarding optimization shipped (drives TTFV <= 3 min)"
    status: pending
    owner: "frontend + product"
    notes: "TTFV instrumented and dashboarded"
  - id: D4
    name: "Public marketing site live"
    status: pending
    owner: "marketing + frontend"
    notes: "Sources weekly_registrations"
  - id: D5
    name: "Metrics dashboard (registrations, TTFV, conversion) live and reviewed"
    status: pending
    owner: "data + founder"
    notes: "Feeds all three hard thresholds"
  - id: D6
    name: "Wave 2 cost-budget.yaml review with adjusted caps if needed"
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

# Gate: Wave 2 → Wave 3

## Hard thresholds (must-pass)

### `weekly_registrations >= 100`

Computed as a 4-week rolling average of new cells registered per week, sampled at gate-evaluation time over the last completed 4 weeks of Wave 2. Source: product analytics dashboard (`registrations.weekly_rolling_4w`). Bot registrations and internal test accounts are excluded.

### `ttfv_minutes <= 3`

Median time-to-first-value across new cells registered in the last 30 days:

```
ttfv = time(first_task_approved) - time(registration_completed)
```

Aggregated as median over the 30-day cohort. Source: product analytics. Cells that never reached an approved task within 14 days are excluded from the median (tracked separately as activation rate). Note this threshold is "lower is better".

### `conversion >= 0.05`

Registration-to-paid conversion within a 4-week window:

```
conversion = count(paid within 28 days of registration) / count(registered)
```

Cohort definition: cells registered at least 4 weeks before gate evaluation. Refunds within the 28-day window are subtracted from the numerator. Source: billing service plus product analytics join.

## Deliverables progress

memory-curator auto-syncs deliverable status. This section is rewritten at gate-evaluation time.

## Retrospective themes

_(Founder fills at evaluation time.)_

## Strategic implications for Wave 3

_(Founder fills: depth/retention features, customer-success motion, churn cohort analytics, expected ADR creations.)_

## Risk delta narrative

_(Founder fills around populated risks_delta entries.)_

## Cost-budget review

- Budget cap at gate opening: _per `.claude/agents/_shared/cost-budget.yaml` as adjusted by Wave 1 → 2 review_.
- Actual spend this wave: _to be measured via Langfuse aggregation_.
- Adjustment proposed for Wave 3: _to be decided based on per-customer marginal cost and per-month cap utilization_.
- Founder decision: _pending_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
