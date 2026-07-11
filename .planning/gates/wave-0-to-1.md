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
    description: "AMENDED Phase 00.6 PR-B (per α decision-7, 2026-05-23 grill): Founder runs the canonical 'Market & content brief' demo scenario 10× via `python -m scripts.demo_market_brief --api-base-url https://staging.профики.online/api/v1 --jwt <demo> --cell-id <demo> --runs 10 --output .planning/gates/evidence/wave-0-to-1/` against the actual staging deployment (Timeweb single-box, `staging.профики.online`; YC-стенд снят — RW-06) (cell creation, inline orchestrator-dispatch POST /tasks/{id}/run, Wave-0 deterministic researcher→analyst→writer pipeline — each specialist a real LLM call, artifact generation). Pass criteria (phase-spec § «AC tolerance clarification»): AC8 = cohort p95 latency ≤120s (statistics.quantiles n=20[18]); AC9 = per-run artifact shape (brief ≥1500 RU words, competitive-matrix ≥5×4, content-plan = 10 posts); AC10 = per-run cost ≤30¢ (credits×0.01). Acceptance: ≥9/10 runs pass AC9 + AC10 per-run AND cohort p95 ≤120s (founder may invoke the collector with --tolerate-failures 1 for the ≥9/10 latitude; strict default is 10/10). No manual unblocking of AI loops. summary.json + 10× run_NNN.json + 1× screen-recording uploaded to .planning/gates/evidence/wave-0-to-1/. AC7 (internal demo via UI) DEFERRED to Phase 01.1 retro post-Phase-00.7 frontend ship — Wave-0 anchor closes on API-based demo evidence per Phase 00.6 spec § «Scope amendment 2026-05-23». Reorg per Session-2026-05-15: replaces prior WB-Seller-team-based threshold; WB-Seller vertical now W2 per ADR-017 revision. Prior text (Founder plus 3 friends, web_search execution) superseded — Wave-0 web_search tool-wiring + multi-runner UI deferred to Wave-1 (AC-W1) + Phase 01.1."

deliverables:
  - id: D1
    name: "Wave 0 phases 00.1 through 00.6 phase-specs at B-level (per P-INIT-1)"
    status: done
    owner: "planner + architect"
    notes: "Materialized in Milestone C; phases 00.1–00.7 executed and merged (sync 2026-07-11)"
  - id: D2
    name: "Phase 00.7 (frontend skeleton via Claude Design) added and executed"
    status: done
    owner: "planner"
    notes: "Per Session 1 DECISION-1; phase added in Milestone C; executed and merged (sync 2026-07-11)"
  - id: D3
    name: "Auth, multitenancy, RBAC, LLM-gateway, agents, tasks backend ready"
    status: done
    owner: "backend-implementer"
    notes: "Per contracts/<context>/ Wave 0 critical contexts; delivered in 00.2–00.6, hardened through Wave 1 (sync 2026-07-11)"
  - id: D4
    name: "Deep role-prompts for productivity-core (4 files in contracts/role-prompts/) first-draft + 'Market & content brief' demo-scenario reproducibility on staging"
    status: done
    owner: "backend-implementer + planner"
    notes: "Per Session-2026-05-15 reorg. WB-Seller golden-dataset (30 tasks) preserved in verticals/wb-seller/ as Wave 2 prep work. Role-prompts shipped and hardened to >=v1.0.0 in Phase 01.1-retro (sync 2026-07-11). Staging demo-reproducibility evidence (anchor-run) remains tracked under RW-07 / DV-08 — see hard threshold."
  - id: D5
    name: "Internal demo recording with 5 reference scenarios completed"
    status: partial
    owner: "founder"
    notes: "Hard-threshold evidence — remains open ONLY as RW-07 anchor-run / DV-08 / DV-09 (demo recording + summary.json evidence); all 00.1-00.7 build work done (sync 2026-07-11)"
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

**Definition (AMENDED Phase 00.6 PR-B, per α decision-7 2026-05-23 — canonical; синхронизировано с frontmatter 2026-07-07 per ADR-040 D12).** Founder runs the canonical **«Market & content brief»** demo scenario **10×** via `python -m scripts.demo_market_brief --api-base-url https://staging.профики.online/api/v1 --runs 10` against the actual staging deployment (Timeweb single-box, `staging.профики.online`; YC-стенд снят — RW-06). Pipeline: Wave-0 deterministic researcher→analyst→writer, each specialist a real LLM call, artifact generation.

**Acceptance (per frontmatter description — authoritative):**
- AC8 = cohort p95 latency ≤120s (`statistics.quantiles n=20[18]`)
- AC9 = per-run artifact shape: `brief.md` ≥1500 RU words, competitive-matrix ≥5×4, content-plan = 10 posts
- AC10 = per-run cost ≤30¢
- ≥9/10 runs pass AC9+AC10 AND cohort p95 ≤120s (`--tolerate-failures 1`; strict default 10/10)
- No manual unblocking of AI loops

**Evidence required.** `summary.json` + 10× `run_NNN.json` + 1× screen-recording uploaded to `.planning/gates/evidence/wave-0-to-1/`. Tracked as [DV-08](../DEFERRED-VERIFICATION.md) / [RW-07](../FOUNDER-RUNWAY.md).

> **Superseded definitions (history):** (1) WB-Seller team-based threshold — superseded per Session-2026-05-15 reorg (WB-Seller vertical → Wave 2); (2) «Founder plus 3 friends, web_search execution» — superseded per α decision-7 (2026-05-23): friend-runs → Wave-2 phase 02.0, web_search tool-wiring → Wave 1. AC7 (demo via UI) deferred to Phase 01.1-retro post-00.7.

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
