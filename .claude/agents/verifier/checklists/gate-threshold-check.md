# Checklist — wave→wave gate-threshold check

Run before any `.planning/gates/wave-N-to-N+1.md` flips from `PENDING`
to `PASSED`. AND-combined: a single threshold failing blocks the
transition regardless of others passing (per ADR-025 §2).

## 0. Preconditions (must)

- [ ] Gate-file exists at `.planning/gates/wave-N-to-N+1.md` with
      `status: PENDING` and complete `hard_thresholds` frontmatter.
- [ ] memory-curator has pre-filled `actual` values (verifier
      independently re-queries; pre-fill is input only).
- [ ] Verifier never trusts the pre-fill alone — every threshold is
      re-measured.
- [ ] Output dir created: `verification-reports/gates/wave-N-to-N+1/<rfc3339>/`.

## 1. Wave 0 → 1 (must, AND-combined)

| Key | Required | Measurement method | Verifier action |
|---|---|---|---|
| `internal_demo.passed` | `= true` | founder confirmation in phase-state | cross-check `phase-state:wave-0-foundation` for `internal_demo_confirmed: true` envelope; capture screenshot/log |

- [ ] `internal_demo.passed` confirmed → PASS.
- [ ] Anything else → FAIL.

## 2. Wave 1 → 2 (must, AND-combined)

| Key | Required | Measurement method | Verifier action |
|---|---|---|---|
| `friend_feedback.nps` | `>= 30` | aggregate from `_meta/verticals/<slug>/friend-feedback/*.yaml` | run `python -m oriion.acceptance.runner gate wave-1-to-2 --metric nps`; formula = promoters_pct − detractors_pct, range −100..100 |
| `acceptance_criteria_pass_rate` | `>= 0.9` | rollup last 30d verifier runs | scan `verification-reports/*` for `verdict=pass` / total in window |

- [ ] BOTH thresholds PASS → gate PASS.
- [ ] Any threshold FAIL → gate FAIL.

## 3. Wave 2 → 3 (must, AND-combined)

| Key | Required | Measurement method | Verifier action |
|---|---|---|---|
| `weekly_registrations` | `>= 100` | SQL on analytics: `count(distinct user_id)` per ISO-week | run `python -m oriion.acceptance.runner gate wave-2-to-3 --metric registrations`; capture last 4 ISO weeks; threshold must hold for the **latest** completed week |
| `TTFV_minutes` | `<= 3` | p50 of analytics event sequence `signup→first-value` | capture p50 + p95 for completeness; verdict on p50 |
| `conversion` | `>= 0.05` | paying / registered cohort over 14d window | use 14-day rolling cohort ending at gate-evaluation date |

- [ ] ALL THREE thresholds PASS → gate PASS.
- [ ] Any FAIL → gate FAIL.

## 4. Wave 3 → 4 (must, AND-combined)

| Key | Required | Measurement method | Verifier action |
|---|---|---|---|
| `paying_customers` | `>= 500` | `billing.subscriptions where status='active' and paid_last_30d` | distinct customer count |
| `MRR_RUB` | `>= 3_000_000` | sum(monthly_recurring_revenue_rub) across active subs | run `python -m oriion.acceptance.runner gate wave-3-to-4 --metric mrr` |

- [ ] BOTH thresholds PASS → gate PASS.
- [ ] Any FAIL → gate FAIL.

## 5. Wave 4 → 5 (must, AND-combined)

| Key | Required | Measurement method | Verifier action |
|---|---|---|---|
| `paying_customers` | `>= 2000` | same as Wave 3→4 | distinct customer count |
| `MRR_RUB` | `>= 15_000_000` | same as Wave 3→4 | sum across active subs |

- [ ] BOTH thresholds PASS → gate PASS.
- [ ] Any FAIL → gate FAIL.

## 6. Capture (must — every wave-pair)

- [ ] Raw measurement output saved to
      `verification-reports/gates/wave-N-to-N+1/<rfc3339>/<key>.json`.
- [ ] Summary `gate-report.md` with one row per threshold:
      `key | required | actual | status | method | source-artefact`.

## 7. Verdict emit (must)

- [ ] All thresholds PASS → `tech.oriion.phase.complete.v1` with
      `subject: gate/wave-N-to-N+1` and the captured `actual` values.
      memory-curator updates frontmatter; founder applies narrative +
      `status: PASSED`.
- [ ] Any FAIL → `tech.oriion.acceptance.failed.v1` with
      `subject: gate/wave-N-to-N+1`, `reason: gate-threshold-not-met`,
      threshold_results listing every key with required/actual/status.

## Hard rules

- AND-combined. No "two of three is good enough".
- Verifier never flips `status`. memory-curator + founder mutate the
  gate-file.
- No retry-to-green: measurement is a single read; if fail today, gate
  fails today.
- Per ADR-025 §3: only founder sets `status: PASSED | BLOCKED`. Verifier
  produces the precondition evidence.
