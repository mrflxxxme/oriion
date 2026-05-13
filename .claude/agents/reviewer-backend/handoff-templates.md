# reviewer-backend — handoff templates

CloudEvents 1.0 envelopes. Schema authority: `.claude/agents/_shared/handoff-schema.json`.

## Inbound

### `tech.oriion.code.commit.v1` (from backend-implementer)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.code.commit.v1",
  "source": "agent://backend-implementer",
  "id": "<ulid>",
  "time": "<rfc3339>",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "branch": "feature/wave-0-phase-00.2-custom-jwt-auth",
    "head_sha": "<sha>",
    "tier": 3,
    "bounded_contexts_touched": ["iam"],
    "contracts_touched": ["_meta/contracts/iam/api.yaml", "_meta/contracts/iam/schema.sql"],
    "migrations_included": true,
    "adr_refs": ["ADR-007", "ADR-014"],
    "acceptance_criteria_ids": ["AC-00.2-01", "AC-00.2-02"],
    "cycle": 1
  }
}
```

## Outbound

### `tech.oriion.review.report.v1` — verdict = approve

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.report.v1",
  "source": "agent://reviewer-backend",
  "id": "<ulid>",
  "time": "<rfc3339>",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "verdict": "approve",
    "cycle": 1,
    "minor_findings": [
      {"file": "backend/src/iam/jwt.py", "line": 87, "note": "consider extracting rotation window to settings"}
    ],
    "checklist_run": ["pr-review-backend", "migration-safety"],
    "next_role": "verifier"
  }
}
```

### `tech.oriion.review.report.v1` — verdict = escalate

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.report.v1",
  "source": "agent://reviewer-backend",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "data": {
    "verdict": "escalate",
    "cycle": 3,
    "reason": "cycle-cap-reached",
    "escalation_partner": "architect",
    "history_ref": "revisions/00.2-reviewer-backend.md",
    "next_role": "architect"
  }
}
```

### `tech.oriion.review.revision.v1` — verdict = request_changes

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.revision.v1",
  "source": "agent://reviewer-backend",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "cycle": 1,
    "revisions_file": "revisions/00.2-reviewer-backend.md",
    "block_count": 2,
    "major_count": 1,
    "minor_count": 4,
    "next_role": "planner"
  }
}
```

## `revisions/<phase-id>-reviewer-backend.md` template

```markdown
---
phase_id: <id>
reviewer: reviewer-backend
cycle: <n>
head_sha: <sha>
opened_at: <rfc3339>
---

# Revision request — phase <id> — cycle <n>

## Blockers (must fix)
| # | severity | file:line | axis | observed | expected | suggested-fix |
|---|---|---|---|---|---|---|
| 1 | block | backend/src/iam/jwt.py:42 | contract | returns 500 on expired token | api.yaml says 401 | raise HTTPException(401, code="token_expired") |

## Major (should fix)
...

## Minor (nice to have)
...

## Cycle history
- cycle 1 — <link to this file>
```
