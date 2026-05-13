# verifier — handoff templates

CloudEvents 1.0 envelopes. Schema authority:
`.claude/agents/_shared/handoff-schema.json`.

## Inbound

### `tech.oriion.review.report.v1` — approved verdicts fan-in

Verifier waits until the AND of all required reviewers for the PR
(`reviewer-backend` always; `reviewer-security` always for tier 3+;
`reviewer-frontend` if PR touches UI) is `verdict: approve`. One sample:

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.report.v1",
  "source": "agent://reviewer-backend",
  "subject": "phase/00.2/pr/42",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "verdict": "approve",
    "next_role": "verifier"
  }
}
```

Verifier checks against a known required-reviewer set per the PR's
tier (read from the commit envelope) before starting.

## Outbound

### `tech.oriion.phase.complete.v1` — all AC pass

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.phase.complete.v1",
  "source": "agent://verifier",
  "id": "<ulid>",
  "time": "<rfc3339>",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "verdict": "pass",
    "acceptance_results": [
      {"id": "AC-00.2-01", "test": "backend/tests/iam/test_jwt.py::test_refresh_rotates_token", "status": "PASS", "duration_ms": 142},
      {"id": "AC-00.2-02", "test": "tests/e2e/auth/login.spec.ts::login_happy_path", "status": "PASS", "duration_ms": 4310}
    ],
    "metrics_snapshot": {
      "test_count": 2,
      "pass_count": 2,
      "fail_count": 0,
      "wall_clock_ms": 4452,
      "p95_latency_ms": 87,
      "error_rate": 0.0
    },
    "artefacts_dir": "verification-reports/00.2/2026-05-13T14-30-00Z/",
    "next_role": "memory-curator"
  }
}
```

### `tech.oriion.phase.complete.v1` — wave-transition variant

`subject` becomes `gate/wave-N-to-N+1`, body shape adapts:

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.phase.complete.v1",
  "source": "agent://verifier",
  "subject": "gate/wave-1-to-2",
  "data": {
    "gate": "wave-1-to-2",
    "verdict": "pass",
    "threshold_results": [
      {"key": "friend_feedback_nps", "required": ">=30", "actual": 34, "status": "PASS", "method": "survey-export"},
      {"key": "acceptance_criteria_pass_rate", "required": ">=0.9", "actual": 0.94, "status": "PASS", "method": "rollup-of-verifier-runs"}
    ],
    "measurement_artefacts_dir": "verification-reports/gates/wave-1-to-2/2026-09-01T12-00-00Z/",
    "next_role": "memory-curator"
  }
}
```

### `tech.oriion.acceptance.failed.v1` — any AC red OR missing test

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.acceptance.failed.v1",
  "source": "agent://verifier",
  "subject": "phase/<phase-id>/pr/<pr-number>",
  "data": {
    "phase_id": "00.2",
    "pr_number": 42,
    "head_sha": "<sha>",
    "verdict": "fail",
    "reason": "criterion-failed | missing-test-for-criterion | flaky-test | gate-threshold-not-met | missing-test-runner | tool-violation",
    "acceptance_results": [
      {"id": "AC-00.2-01", "status": "PASS", "test": "...::ok"},
      {"id": "AC-00.2-02", "status": "FAIL", "test": "...::login_happy_path", "assertion": "expected 200, got 401", "duration_ms": 4310},
      {"id": "AC-00.2-03", "status": "MISSING", "note": "no test covers this criterion"}
    ],
    "artefacts_dir": "verification-reports/00.2/2026-05-13T14-30-00Z/",
    "next_role": "planner"
  }
}
```

### `tech.oriion.acceptance.failed.v1` — wave-transition variant

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.acceptance.failed.v1",
  "source": "agent://verifier",
  "subject": "gate/wave-1-to-2",
  "data": {
    "gate": "wave-1-to-2",
    "verdict": "fail",
    "reason": "gate-threshold-not-met",
    "threshold_results": [
      {"key": "friend_feedback_nps", "required": ">=30", "actual": 22, "status": "FAIL", "method": "survey-export"},
      {"key": "acceptance_criteria_pass_rate", "required": ">=0.9", "actual": 0.91, "status": "PASS", "method": "rollup-of-verifier-runs"}
    ],
    "next_role": "planner"
  }
}
```

## `verification-reports/<phase-id>/<rfc3339>/report.md` template

```markdown
---
phase_id: <id>
pr_number: <n>
head_sha: <sha>
run_started: <rfc3339>
run_completed: <rfc3339>
verdict: pass | fail
---

# Verification report — phase <id> — <rfc3339>

## Results
| AC-ID | Statement | Test | Status | Duration | Artefact |
|---|---|---|---|---|---|
| AC-00.2-01 | Refresh token rotates atomically | backend/tests/iam/test_jwt.py::test_refresh_rotates_token | PASS | 142ms | junit.xml |
| AC-00.2-02 | Prior refresh-token invalidated | backend/tests/iam/test_jwt.py::test_refresh_invalidates_prior | PASS | 88ms | junit.xml |

## Failures (if any)
- AC-NN-NN — <assertion> at <test-file:line>

## Metrics
- wall_clock_ms: ...
- p95_latency_ms: ...
- error_rate: ...

## Notes
- flake re-runs: 0
- under-spec criteria: 0
```
