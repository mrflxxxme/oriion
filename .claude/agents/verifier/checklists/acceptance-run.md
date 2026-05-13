# Checklist — acceptance run (per-phase)

Run for every PR after all required reviewers approved. Output: verdict
envelope + `verification-reports/<phase-id>/<rfc3339>/report.md`.

## 1. Pre-run preconditions (must)

- [ ] All required reviewers have emitted `verdict: approve` for the
      current `head_sha`.
- [ ] PR `head_sha` is the latest commit on the branch (no new pushes
      since reviewer approval).
- [ ] PHASE.md exists at `.planning/phases/<phase-id>/PHASE.md` and
      contains a `## Acceptance criteria` section.

If any precondition fails → do **not** run; emit
`acceptance.failed.v1` with `reason: precondition-not-met`.

## 2. Criterion enumeration (must — all covered)

- [ ] Every AC-ID in PHASE.md is enumerated.
- [ ] Every AC-ID has at least one mapped test (unit / integration /
      E2E / perf / acceptance-runner).
- [ ] Any AC-ID without a mapped test → emit
      `reason: missing-test-for-criterion` and STOP. Do not improvise.

## 3. Run dir (must)

- [ ] `verification-reports/<phase-id>/<rfc3339>/` created.
- [ ] `run.yaml` written with: phase_id, pr_number, head_sha,
      criterion→test mapping, start timestamp.

## 4. Test execution order (must)

- [ ] Unit tests run first (`pytest -q --junitxml=...`).
- [ ] Integration tests run after unit pass / regardless (always run all
      AC tests; do NOT short-circuit).
- [ ] E2E run after integration.
- [ ] Perf run last.
- [ ] All stdout / stderr / exit-code captured to artefact dir.
- [ ] junit-xml or equivalent structured output captured per suite.

## 5. Flake heuristic (must)

- [ ] On first-run failure: look up test-id in
      `agent-memory:verifier / flaky-tests`.
- [ ] If match → re-run **exactly once** with same command.
- [ ] Second-run is the verdict (PASS or FAIL).
- [ ] If second-run also FAIL → mark with `flake-suspected: true` in
      report; verdict stays FAIL.
- [ ] Never re-run more than once. Never re-run if no flake-pattern
      match.

## 6. Exit-code discipline (must)

- [ ] Every test runner exit-code recorded in artefact dir
      (`exit-codes.json`).
- [ ] Verdict `pass` requires every recorded exit-code = 0.
- [ ] Single non-zero exit-code → verdict = `fail`.

## 7. Artefact capture (must)

- [ ] junit-xml for pytest + playwright.
- [ ] Playwright screenshots / videos on failure.
- [ ] k6 summary-export JSON for perf runs.
- [ ] curl smoke outputs (`-o` files).

## 8. Report composition (must)

- [ ] `report.md` written with frontmatter (phase_id, pr_number,
      head_sha, run_started, run_completed, verdict).
- [ ] Results table covers every AC-ID with status + test + duration +
      artefact link.
- [ ] Failures section enumerates assertion + test file:line for each
      FAIL.
- [ ] Metrics block populated (test_count, pass_count, fail_count,
      wall_clock_ms, p95_latency_ms, error_rate where applicable).

## 9. Verdict emit (must)

- [ ] All AC = PASS → `tech.oriion.phase.complete.v1` to memory-curator.
- [ ] Any AC = FAIL OR any MISSING → `tech.oriion.acceptance.failed.v1`
      to planner with explicit `reason` field.

## 10. Memory upsert (must)

- [ ] New flake pattern observed → append to `flaky-tests`.
- [ ] Run summary appended to `recent_runs` window for phase.
- [ ] If new criteria shape observed → upsert template.

## Hard rules

- Binary verdict. No partial credit.
- Never modify a test to make it pass.
- Never skip a declared AC.
- Never invent a new AC.
- If acceptance is under-specified → bounce to planner, never approve.
