# verifier — memory

## Namespace

`agent-memory:verifier` (AgentDB, ONNX 384-dim, HNSW index per ADR-023
§6-7).

## What persists across sessions

### 1. Flaky-test patterns

Keyed by `test-id` + classification. Used by the flake heuristic in
`workflows.md` playbook 1 + by playbook 3 triage.

```yaml
- test_id: tests/e2e/auth/login.spec.ts::login_happy_path
  classification: environmental-timeout
  pattern: "navigation timeout at /dashboard on cold-start"
  occurrences: 7
  first_seen: <date>
  last_seen: <date>
  reproduction_hints:
    - "happens when no warm DB connection pool"
    - "passes deterministically with --workers=1"
  current_action: re-run-once-on-first-fail
  retire_when: implementer-adds-explicit-wait-OR-CI-warmup-step
```

When `occurrences >= 5`, verifier raises a `spec-drift-or-test-instability`
note in the next phase report.

### 2. Acceptance-criteria templates by phase-type

Reusable shapes the verifier has observed across phases. Helps surface
"missing test" gaps faster.

```yaml
- phase_type: backend-endpoint
  typical_criteria:
    - "endpoint returns documented status code for happy input"
    - "endpoint returns documented status code for each declared error"
    - "endpoint enforces auth + RLS"
    - "endpoint emits expected event(s)"
    - "p95 latency under <threshold>"
- phase_type: frontend-page
  typical_criteria:
    - "page renders on supported viewports"
    - "primary action completes happy path"
    - "empty / loading / error states render"
    - "a11y AA passes (axe)"
- phase_type: migration
  typical_criteria:
    - "upgrade + downgrade roundtrip on fixture DB"
    - "data integrity preserved (row-count, checksum)"
    - "RLS policies active on touched tables"
```

### 3. Gate-threshold measurement methods

Per wave-pair, how to re-query the `actual` value independent of
memory-curator's pre-fill. Used by `checklists/gate-threshold-check.md`.

```yaml
- wave_pair: wave-0-to-1
  thresholds:
    - key: internal_demo.passed
      method: "founder-confirmation envelope present in phase-state"
      verifier_action: "read .planning/gates/wave-0-to-1.md notes + cross-check phase-state:wave-0-foundation"
- wave_pair: wave-1-to-2
  thresholds:
    - key: friend_feedback_nps
      method: "aggregate from _meta/verticals/<slug>/friend-feedback/*.yaml"
      verifier_action: "python -m oriion.acceptance.runner gate wave-1-to-2"
      formula: "promoters_pct - detractors_pct (range -100..100)"
    - key: acceptance_criteria_pass_rate
      method: "rollup of last 30d verifier runs"
      verifier_action: "scan verification-reports/* for verdict=pass / total"
- wave_pair: wave-2-to-3
  thresholds:
    - key: weekly_registrations
      method: "SQL against analytics: count(distinct user_id) per ISO-week"
    - key: TTFV_minutes
      method: "p50 from analytics event sequence signup→first-value"
    - key: conversion
      method: "paying / registered cohort over 14d window"
- wave_pair: wave-3-to-4
  thresholds:
    - key: paying_customers
      method: "billing.subscriptions where status='active' + paid in last 30d"
    - key: MRR_RUB
      method: "sum(monthly_recurring_revenue_rub) across active subscriptions"
- wave_pair: wave-4-to-5
  thresholds:
    - key: paying_customers
      method: "same as wave-3-to-4"
    - key: MRR_RUB
      method: "same as wave-3-to-4"
```

### 4. Last-N runs per phase (trend window)

Rolling N=10 most recent verifier runs per phase, used for trend
detection (regressions, time-to-green deterioration).

```yaml
- phase_id: 00.2
  recent_runs:
    - {at: <rfc3339>, verdict: pass, pass_count: 12, fail_count: 0, wall_ms: 4500}
    - {at: <rfc3339>, verdict: fail, pass_count: 11, fail_count: 1, wall_ms: 4600, fail_ids: [AC-00.2-04]}
    - ...
```

## What does NOT persist

- Full test stdout / stderr (lives in `verification-reports/`).
- Source code content (re-read from disk).
- Phase-spec text (re-read).
- Gate-file content (re-read).
- Any secret captured from a test failure trace.

## Write triggers

- After every verdict → upsert flake-pattern occurrences, append run to
  recent-runs window.
- After playbook 3 investigation → upsert classification.
- After observed phase-type → upsert criteria template.

## Read triggers

- Pipeline start: load namespace.
- Before each test → flake heuristic lookup by test-id.
- Before gate check → measurement-method lookup by wave-pair.

## Eviction

- `recent_runs` window: keep last 10 per phase; older runs archived by
  memory-curator monthly.
- `flaky-tests`: retired when implementer commits a fix and 5
  consecutive subsequent runs are green; verifier marks `retired: true`
  but keeps the entry for audit history.
