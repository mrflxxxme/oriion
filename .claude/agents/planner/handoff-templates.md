# planner — handoff templates

CloudEvents 1.0 envelopes (ADR-024 §3). Common envelope:

```yaml
specversion: "1.0"
type: <event-type>
source: claude-agent://planner
id: <uuid-v4>
time: <ISO-8601>
datacontenttype: application/json
subject: <phase-id>
data: <payload>
```

---

## Inbound events

### `tech.oriion.phase.spec.v1`

**From:** founder
**Trigger:** founder открыл новый phase из roadmap, готов phase-spec, нужна decomposition.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  wave: 0
  spec_file: ".planning/roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md"
  status: "B-level-ready"
  pipeline_template: "backend-feature"
  founder_notes: "Priority: high. Friend-loop starts next week."
```

**Planner response:** Workflow 1 (decomposition).

---

### `tech.oriion.review.revision.v1`

**From:** `reviewer-backend`, `reviewer-frontend`, `reviewer-security`
**Trigger:** reviewer вернул revision-request на PR.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  reviewer: "reviewer-security"
  pr_ref: "feature/wave-0-phase-00.2-custom-jwt-auth"
  pr_sha: "abc1234"
  revision_doc: ".planning/.../revisions/00.2-reviewer-security.md"
  findings_count:
    blocker: 1
    high: 2
    medium: 0
    low: 0
  current_cycle: 2
  max_cycles: 3
```

**Planner response:** Workflow 2 (re-plan). Если current_cycle = 3 — escalate.

---

### `tech.oriion.adr.merged.v1`

**From:** `memory-curator` после founder approve нового ADR
**Trigger:** новый ADR может требовать decomposition в backlog phase tasks.

**Payload schema:**

```yaml
data:
  adr_id: "ADR-028"
  adr_file: ".planning/decisions/ADR-028-vertical-prompt-semver.md"
  affected_contexts: ["agents"]
  follow_up_phases: ["00.5"]  # phases которые нужно re-plan
  founder_directive: "Apply to Phase 00.5 within next sprint" | null
```

**Planner response:** Если `follow_up_phases` non-empty — re-plan affected phases (Workflow 2-like). Иначе acknowledge + memory_store для future reference.

---

## Outbound events

### `tech.oriion.plan.task.v1`

**To:** `backend-implementer`, `frontend-implementer` (batch per role)
**Trigger:** PLAN.md ready, dispatch tasks к implementers.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  plan_file: ".planning/roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth/PLAN.md"
  target_role: "backend-implementer"
  cycle: 1
  tasks:
    - id: "T1"
      description: "Alembic migration: add users table per _meta/contracts/iam/schema.sql"
      depends_on: []
      parallel_group: "A"
      estimated_tier: 3
      acceptance_check: "verifier T1: migration up + down succeeds; tests/iam/test_migrations.py passes"
      contract_refs:
        - "_meta/contracts/iam/schema.sql#users"
      adr_refs: ["ADR-007"]
    - id: "T2"
      description: "Pydantic schemas User, UserCreate per _meta/contracts/iam/api.yaml"
      depends_on: ["T1"]
      parallel_group: "A"
      estimated_tier: 2
      acceptance_check: "verifier T2: pytest tests/iam/test_schemas.py::test_user_validation"
      contract_refs:
        - "_meta/contracts/iam/api.yaml#User"
        - "_meta/contracts/iam/api.yaml#UserCreate"
      adr_refs: []
  handoff_after_complete:
    next_role: "reviewer-backend"
    next_role_parallel: "reviewer-security"
    next_event: "tech.oriion.code.commit.v1"
```

---

### `tech.oriion.plan.ui_phase.v1`

**To:** `designer`
**Trigger:** phase-spec имеет `ui-spec:` секцию. Дispatched FIRST в pipeline.

**Payload schema:**

```yaml
data:
  phase_id: "00.7"
  plan_file: ".planning/roadmap/wave-0-foundation/phases/00.7-frontend-skeleton/PLAN.md"
  ui_spec_extract:
    pages:
      - slug: "cells-list"
        layout: "dashboard"
        content_slots: ["header", "sidebar", "main-table", "empty-state"]
        interaction_states: ["loading", "empty", "error", "populated"]
        a11y_must_have: ["keyboard-nav", "screen-reader-labels", "focus-trap"]
    components_used: ["Button", "Card", "Table", "EmptyState", "Skeleton"]
    new_components_needed: []
  design_token_set: "nordic-warm"
  inventory_ref: "_meta/ui/component-inventory.md"
  handoff_after_complete:
    next_role: "frontend-implementer"
    next_event: "tech.oriion.design.ready.v1"
```

---

### `tech.oriion.conflict.escalation.v1`

**To:** `architect`
**Trigger:** policy-gap, reviewer-disagreement, или cycle-exhaustion detected.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  conflict_type: "policy-gap" | "reviewer-disagreement" | "cycle-exhaustion"
  context:
    plan_file: ".planning/.../PLAN.md"
    revision_docs:
      - ".planning/.../revisions/00.2-reviewer-backend.md"
      - ".planning/.../revisions/00.2-reviewer-security.md"
    cycle_count: 3
  planner_notes: "Disagreement on rate-limit on /auth/refresh. Need policy decision."
```

---

### `tech.oriion.spec.incomplete.v1`

**To:** founder
**Trigger:** phase-spec не B-level per P-INIT-1.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  spec_file: ".planning/.../phases/00.2-custom-jwt-auth.md"
  missing_items:
    - "inline OpenAPI stubs for POST /auth/login, POST /auth/refresh"
    - "test cases (need ≥1 unit + ≥1 integration)"
    - "ui-spec: section (phase touches frontend per file-tree)"
  proposed_action: "founder upgrades spec to B-level before re-trigger"
```

---

## Envelope validation

Каждый outbound event валидируется против `.claude/agents/_shared/handoff-schema.json`
перед emit. Если payload не conform — error log + abort + escalate к founder.
