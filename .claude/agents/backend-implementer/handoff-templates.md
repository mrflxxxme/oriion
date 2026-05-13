# backend-implementer — handoff templates

CloudEvents 1.0 envelopes (ADR-024 §3). Common envelope:

```yaml
specversion: "1.0"
type: <event-type>
source: claude-agent://backend-implementer
id: <uuid-v4>
time: <ISO-8601>
datacontenttype: application/json
subject: <phase-id>
data: <payload>
```

---

## Inbound events

### `tech.oriion.plan.task.v1`

**From:** `planner`
**Trigger:** PLAN.md ready, batch tasks для backend-implementer.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  plan_file: ".planning/roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth/PLAN.md"
  target_role: "backend-implementer"
  cycle: 1   # 2 or 3 if re-plan
  tasks:
    - id: "T1"
      description: "Alembic migration: add users table per _meta/contracts/iam/schema.sql"
      depends_on: []
      parallel_group: "A"
      estimated_tier: 3
      acceptance_check: "verifier T1: alembic upgrade + downgrade succeeds; tests/iam/test_migrations.py passes"
      contract_refs:
        - "_meta/contracts/iam/schema.sql#users"
      adr_refs: ["ADR-007", "ADR-009"]
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
  revision_doc: null   # populated если cycle > 1: path к revisions/<phase>-reviewer-*.md
```

**Implementer response:**
- For each task: run appropriate Workflow (1-3) based on task type
- If cycle > 1 AND revision_doc set: Workflow 4
- Respect depends_on ordering, parallelize within group
- Emit `tech.oriion.code.commit.v1` after each commit

---

## Outbound events

### `tech.oriion.code.commit.v1`

**To:** `reviewer-backend` AND `reviewer-security` (parallel emit per ADR-023 §3)
**Trigger:** atomic commit made.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  task_id: "T1"
  commit_sha: "abc1234"
  commit_message_summary: "feat(iam): add users table migration"
  bounded_context: "iam"
  files_changed:
    - path: "backend/alembic/versions/iam/0001_users.py"
      lines_added: 47
      lines_removed: 0
    - path: "backend/tests/iam/test_migrations.py"
      lines_added: 32
      lines_removed: 0
  contract_refs:
    - "_meta/contracts/iam/schema.sql#users"
  adr_refs: ["ADR-007", "ADR-009"]
  tests_added:
    - "tests/iam/test_migrations.py::test_users_table_exists"
    - "tests/iam/test_migrations.py::test_users_rls_policy_active"
    - "tests/iam/test_migrations.py::test_downgrade_cleans"
  acceptance_check_mapped: "verifier T1"
  self_audit_checklist: ".claude/agents/backend-implementer/checklists/migration-checklist.md"
  self_audit_passed: true
  cycle: 1
```

---

### `tech.oriion.conflict.escalation.v1`

**To:** `architect`
**Trigger:** detected gap requiring escalation: contract-spec gap, cross-context coupling
need, naming-correction-needed-on-existing-code.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  conflict_type: "contract-spec-gap" | "cross-context-coupling-need" | "naming-correction-needed" | "rls-policy-missing-in-spec"
  context:
    task_id: "T3"
    detail: "Task требует endpoint POST /auth/2fa/verify, но spec в _meta/contracts/iam/api.yaml отсутствует"
    contract_ref_attempted: "_meta/contracts/iam/api.yaml#/paths/~1auth~1twoFA~1verify"
    grep_result: "no match"
  implementer_action_taken: "blocked-task-pending-resolution"
  rationale: "P-INIT-2: contracts authoritative, не могу inline create endpoint без spec"
```

---

### `tech.oriion.task.unclear.v1`

**To:** founder
**Trigger:** task description ambiguous даже после reading PLAN.md + contracts.

**Payload schema:**

```yaml
data:
  phase_id: "00.2"
  task_id: "T7"
  task_description: "Add token refresh logic"
  ambiguities:
    - "Token TTL не specified в spec — 15min? 1h? 24h?"
    - "Refresh rotation strategy: single-use (revoke old) vs reusable until expiry?"
    - "Storage: Redis vs DB?"
  contracts_consulted:
    - "_meta/contracts/iam/api.yaml"
    - "_meta/contracts/iam/schema.sql"
  founder_input_requested: "either inline в task description или escalate к architect для new ADR"
```

---

### `tech.oriion.memory.deprecate.v1`

**To:** `memory-curator`
**Trigger:** identified obsolete pattern в own namespace.

**Payload schema:**

```yaml
data:
  requesting_role: "backend-implementer"
  namespace: "agent-memory:backend-implementer"
  key: "fastapi-pattern-pre-async"
  reason: "Project fully migrated к async, sync patterns no longer used"
  preserve_in_archive: true
```

---

## Envelope validation

Каждый outbound event валидируется против `.claude/agents/_shared/handoff-schema.json`
перед emit. Invalid → error log + abort emit + escalate к founder.

## Commit ↔ event timing

Order matters:
1. Make commit (`git commit`)
2. Verify commit succeeded (`git log -1`)
3. Capture sha
4. Emit `tech.oriion.code.commit.v1` с captured sha

Никогда не emit event ДО successful commit (reviewers будут scanning non-existent sha).
