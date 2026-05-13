---
gate: wave-1-to-2
status: PENDING
opened_at: 2026-05-13T12:00:00Z
closed_at: null
founder_signature: null

hard_thresholds:
  friend_feedback_nps:
    target: 30
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "NPS across 3-5 ICP-friends per vertical (5 verticals -> 15-25 friends total). Calculated as (% promoters - % detractors) per ADR-026 sections 3-4 Level C friend-loop methodology. Survey conducted at end of Wave 1 after 30 days of active use."
  acceptance_criteria_pass_rate:
    target: 0.9
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Share of automated acceptance-tests passed against total executed across every Wave 1 phase (verifier role gating). Computed as count(passed) / count(total) over the verifier's run log for Wave 1."

deliverables:
  - id: D1
    name: "All 10 Wave 1 phases delivered per .planning/roadmap/wave-1-core-mvp/"
    status: pending
    owner: "planner + role-leads"
    notes: "Each phase passes its own verifier acceptance gate before counting toward this deliverable"
  - id: D2
    name: "5 verticals (WB-Seller + 4 more) shipped with full prompts + golden-dataset >=75% pass rate"
    status: pending
    owner: "vertical-prompt-author + evaluator"
    notes: "Per ADR-026 section 3 Level B threshold"
  - id: D3
    name: "Friend-loop activated: 3-5 ICP-friends per vertical, >=80% positive sentiment"
    status: pending
    owner: "founder + research"
    notes: "Per ADR-026 sections 3-4 Level C; feeds friend_feedback_nps threshold"
  - id: D4
    name: "Wave 1 cost-budget.yaml review with adjusted caps if needed"
    status: pending
    owner: "founder"
    notes: "Mandatory per cost-budget.yaml review_trigger"
  - id: D5
    name: "All Wave 1 risks reviewed and register updated"
    status: pending
    owner: "memory-curator + founder"
    notes: "Inputs to risks_delta"

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

# Gate: Wave 1 → Wave 2

## Hard thresholds (must-pass)

### `friend_feedback_nps >= 30`

NPS is computed across 3-5 ICP-friends per vertical, across 5 verticals (15-25 respondents total). Each friend rates "How likely are you to recommend Oriion to another seller/operator in your vertical?" on a 0-10 scale.

- Promoters: 9-10
- Passives: 7-8
- Detractors: 0-6

NPS = % promoters − % detractors. The 30 floor is set per ADR-026 Level C friend-loop. Survey is fielded at the end of Wave 1 after >=30 days of active use; raw responses are stored in `.planning/gates/evidence/wave-1-to-2/nps-survey.csv`.

### `acceptance_criteria_pass_rate >= 0.9`

Each Wave 1 phase ships with a verifier-driven acceptance test suite. This metric aggregates pass counts across every executed test in the wave:

```
pass_rate = count(passed_runs) / count(total_runs)
```

Sources: verifier role's run log, exported to `.planning/gates/evidence/wave-1-to-2/verifier-runs.json`. Failures that were waived by founder count as failures for this metric — waivers do not improve the rate.

## Deliverables progress

memory-curator auto-syncs deliverable status. This section is rewritten at gate-evaluation time.

## Retrospective themes

_(Founder fills at evaluation time.)_

## Strategic implications for Wave 2

_(Founder fills: public-beta readiness, payments integration scope, marketing-site requirements, expected ADR creations.)_

## Risk delta narrative

_(Founder fills around populated risks_delta entries.)_

## Cost-budget review

- Budget cap at gate opening: _per `.claude/agents/_shared/cost-budget.yaml` as adjusted by Wave 0 → 1 review_.
- Actual spend this wave: _to be measured via Langfuse aggregation_.
- Adjustment proposed for Wave 2: _to be decided based on per-task and per-month cap utilization_.
- Founder decision: _pending_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
