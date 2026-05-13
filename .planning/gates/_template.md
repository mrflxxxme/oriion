---
# Gate template — copy and rename to wave-N-to-N+1.md
# Schema: ./_schema/gate.schema.json
# Per ADR-025 section 1 and GRILL-DECISIONS-ORIION section 5.1 DECISION-9.
#
# Fill protocol:
# - memory-curator auto-fills (80%): metrics_snapshot, deliverables.status,
#   adr_delta, risks_delta, capacity_snapshot
# - Founder fills (20%): hard_thresholds.actual + passed, status,
#   founder_signature, narrative sections in body

gate: wave-N-to-N+1
status: PENDING
opened_at: YYYY-MM-DDTHH:MM:SSZ
closed_at: null
founder_signature: null

hard_thresholds:
  threshold_key:
    target: 0
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Why this threshold matters and how it is measured"

deliverables:
  - id: D1
    name: "Deliverable name"
    status: pending  # pending | in_progress | done | deferred | cancelled
    owner: "<role or founder>"
    notes: ""

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

# Gate: Wave N → Wave N+1

## Hard thresholds (must-pass)

<!--
Founder-filled. For each threshold key in frontmatter explain:
- business rationale (why this number and not another)
- measurement method (where the actual reading comes from)
- evidence link (dashboard, recording, dataset)
-->

## Deliverables progress

<!--
memory-curator auto-syncs status from roadmap + phase artifacts; founder adds
narrative around partials, deferrals, scope changes.
-->

## Retrospective themes

<!--
Founder-filled at evaluation time:
- what worked well in this wave
- what didn't work and why
- surprises (positive and negative)
-->

## Strategic implications for the next wave

<!--
Founder-filled:
- scope adjustments required
- pivots being considered
- new ADR candidates surfaced by this wave
-->

## Risk delta narrative

<!--
Founder-filled context around risks_delta entries: which mitigation actions
actually moved the needle, which risks now look heavier than first scored.
-->

## Cost-budget review

<!--
MANDATORY per .claude/agents/_shared/cost-budget.yaml review_trigger:
every gate transition requires a review of cost-budget numbers
against actual capacity_snapshot.total_cost_usd_this_wave.
-->

- Budget cap at gate opening: <value from cost-budget.yaml>
- Actual spend this wave: <value from capacity_snapshot.total_cost_usd_this_wave>
- Adjustment proposed for next wave: <none | new cap + rationale>
- Founder decision: <signed off | revisions needed>

## Sign-off

- **Status:** PENDING | PASSED | BLOCKED | WAIVED
- **Founder signature:** _to be signed when status transitions_
- **Date:** _filled at sign-off_
- **Override justification** (only if status = WAIVED): _required_
