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
    description: "Founder plus 3 friends each run the canonical 'Market & content brief' demo scenario through the horizontal productivity-core team end-to-end (cell creation, coordinator decomposition into 3 parallel sub-tasks, Researcher web_search execution, Analyst LLM-only synthesis, Writer artifact generation, founder approval). All runs produce 3 artifacts meeting spec (brief.md ≥1500w, competitive-matrix.md ≥5×4, content-plan.md = 10 posts), with end-to-end latency ≤120s p95 and cost ≤30¢ per run. No manual unblocking of AI loops. Screen-recording uploaded to .planning/gates/evidence/wave-0-to-1/. Reorg per Session-2026-05-15: replaces prior WB-Seller-team-based threshold; WB-Seller vertical now W2 per ADR-017 revision."

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
    notes: "Per contracts/<context>/ Wave 0 critical contexts"
  - id: D4
    name: "Deep role-prompts for productivity-core (4 files in contracts/role-prompts/) first-draft + 'Market & content brief' demo-scenario reproducibility on staging"
    status: pending
    owner: "backend-implementer + planner"
    notes: "Per Session-2026-05-15 reorg. WB-Seller golden-dataset (30 tasks) preserved in verticals/wb-seller/ as Wave 2 prep work. Wave 0 quality bar = demo scenario passes acceptance criteria + role-prompts hardening backlog handed off to Phase 01.1 retro. Per ADR-026 Level B applies to vertical-templates (W1+) — horizontal preset uses first-draft + replicate-failure-driven hardening pattern."
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

**Definition (revised 2026-05-15).** Founder plus 3 friends each run the canonical **«Market & content brief для нового продукта»** demo scenario through the horizontal `productivity-core` team. User input fixed: «Запускаем платформу AI-команд для SMB в РФ. Сделай нам market brief + контент-план первого месяца». Pipeline: Coordinator decomposes into 3 parallel sub-tasks → Researcher (web_search) gathers competitors + boards/communities + trends → Analyst (LLM-only, no Pyodide W0) synthesizes TAM/SAM + competitive matrix + positioning → Writer produces marketing brief + content plan + tone-of-voice doc → Coordinator synthesizes 3 artifacts.

**Per-run acceptance:**
- 3 artifacts produced: `brief.md` ≥1500 words, `competitive-matrix.md` ≥5 rows × ≥4 columns, `content-plan.md` exactly 10 posts with outlines
- End-to-end latency ≤120 sec p95
- Cost ≤30¢ per run
- No manual unblocking of AI loops

**Evidence required.** Screen recording of demo (≤30 min) + 4 demo-run artifact bundles (founder + 3 friends) uploaded to `.planning/gates/evidence/wave-0-to-1/`. Role-prompts hardening backlog produced and handed to Phase 01.1 retro.

> WB-Seller team-based threshold superseded per Session-2026-05-15 roadmap reorg. WB-Seller vertical (with original 30-task golden-dataset) now shipped in Wave 2.

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
