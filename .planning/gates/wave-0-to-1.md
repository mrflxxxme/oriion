---
gate: wave-0-to-1
status: PENDING
opened_at: 2026-05-13T12:00:00Z
closed_at: null
founder_signature: null

hard_thresholds:
  internal_demo_passed:
    target: true
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Founder plus 3 ICP-friends each complete 5 reference scenarios through WB-Seller team end-to-end (cell creation, coordinator decomposition, researcher gathering, writer generation, founder approval). All 15 scenario runs complete without manual unblocking of AI loops. Screen-recording uploaded to .planning/gates/evidence/wave-0-to-1/."

deliverables:
  - id: D1
    name: "Wave 0 phases 00.1 through 00.6 phase-specs at B-level (per P-INIT-1)"
    status: pending
    owner: "planner + architect"
    notes: "Materialized in Milestone C"
  - id: D2
    name: "Phase 00.7 (frontend skeleton via Claude Design) added and executed"
    status: pending
    owner: "planner"
    notes: "Per Session 1 DECISION-1; phase added in Milestone C"
  - id: D3
    name: "Auth, multitenancy, RBAC, LLM-gateway, agents, tasks backend ready"
    status: pending
    owner: "backend-implementer"
    notes: "Per _meta/contracts/<context>/ Wave 0 critical contexts"
  - id: D4
    name: "WB-Seller team golden-dataset (30 tasks) materialized and evaluator passes"
    status: pending
    owner: "vertical-prompt-author + evaluator"
    notes: "Per ADR-026 section 3 Level B (>=75% golden + 100% adversarial)"
  - id: D5
    name: "Internal demo recording with 5 reference scenarios completed"
    status: pending
    owner: "founder"
    notes: "Hard-threshold evidence"
  - id: D6
    name: "cost-budget.yaml numbers reviewed against Wave 0 actual spend"
    status: pending
    owner: "founder"
    notes: "Per cost-budget.yaml review_trigger"

metrics_snapshot:
  snapshot_taken_at: null
  metrics: {}

adr_delta:
  created:
    - ADR-023
    - ADR-024
    - ADR-025
    - ADR-026
    - ADR-027
  revised:
    - ADR-001
    - ADR-007
    - ADR-010
    - ADR-015
    - ADR-021
  superseded: []

risks_delta:
  opened:
    - R-31
  closed:
    - R-29
  mitigated:
    - R-20
    - R-30
  escalated: []

capacity_snapshot:
  ai_team_roles_active: 11
  total_tasks_completed_this_wave: null
  total_cost_usd_this_wave: null
  average_revision_cycles_per_phase: null
  founder_overrides_count: null
---

# Gate: Wave 0 → Wave 1

## Hard thresholds (must-pass)

### `internal_demo_passed = true`

Wave 0 → 1 has a **single hard threshold** — a successful internal demo.

**Definition.** Founder plus 3 ICP-friends each run 5 reference scenarios through the WB-Seller team (cells creation → coordinator decomposes → researcher gathers → writer generates → founder approves). All 15 scenarios complete without manual unblocking of AI loops.

**Evidence required.** Screen recording of the demo (<=30 minutes) plus the completed-scenarios artifact bundle uploaded to `.planning/gates/evidence/wave-0-to-1/`.

**Why a single threshold.** Wave 0 is foundation building. Quantitative business KPIs (NPS, weekly registrations) are not yet measurable — there is no public traffic. The internal demo is binary proof that the cells-to-tasks-to-artifacts pipeline works end-to-end.

## Deliverables progress

memory-curator auto-syncs deliverable status from the roadmap and phase artifacts. This section is rewritten at gate-evaluation time.

## Retrospective themes

_(Founder fills at evaluation time.)_

## Strategic implications for Wave 1

_(Founder fills: which ADR revisions Wave 1 friend-loop launch requires; scope adjustments for public-beta preparation.)_

## Risk delta narrative

- **R-29 closed** (Milestone A): vertical-expertise gap covered via founder personal operating expertise plus the ADR-026 validation gate.
- **R-31 opened** (Milestone A): AI-cost overrun under the 11-role Opus team. Mitigation active via `cost-budget.yaml` (Conservative defaults: per-task $0.50/$2, per-day $30/$75, per-month kill-switch $500). Wave 0 review: actual spend vs caps — TBD.
- **R-20 / R-30 mitigated** by the mandate-split applied in the Milestone A audit.

## Cost-budget review

- Budget cap (Wave 0 baseline): per-month team kill-switch per `.claude/agents/_shared/cost-budget.yaml`.
- Actual spend this wave: _to be measured via Langfuse aggregation_.
- Adjustment proposed for Wave 1: _depends on actual; default no change unless spend exceeds 60% of cap_.
- Founder decision: _pending_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
