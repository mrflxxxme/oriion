# verifier — workflows

Three playbooks. Inbound envelope + phase-vs-gate context determines
which one runs.

## 1. Per-phase acceptance run (inbound: `tech.oriion.review.report.v1` × N approved)

**Trigger.** Last required reviewer emits `verdict: approve`. Verifier
waits until the AND of all required reviewers is satisfied.

**Steps.**
1. **Read PHASE.md** at `.planning/phases/<phase-id>/PHASE.md`.
   - Extract every `## Acceptance criteria` row into a list of
     `(id, statement, test-hint-if-any)` tuples.
2. **Locate tests per criterion.** Build a mapping:
   ```
   AC-00.2-01 → backend/tests/iam/test_jwt.py::test_refresh_rotates_token
   AC-00.2-02 → backend/tests/iam/test_jwt.py::test_refresh_invalidates_prior
   AC-00.2-03 → tests/e2e/auth/login.spec.ts::login_happy_path
   ```
   - Use `Grep` for criterion ID in test files (project convention: each
     test docstring includes the AC-ID it covers).
   - For NFR criteria (latency, throughput, error budget) → locate
     `tests/perf/<phase-id>/*.js` k6 script.
3. **Detect under-spec.**
   - Any criterion with **no** test → fast-fail with
     `tech.oriion.acceptance.failed.v1`, `reason:
     missing-test-for-criterion`. Routed to `planner`. STOP here.
4. **Create run dir.**
   - `verification-reports/<phase-id>/<rfc3339>/`
   - Write `run.yaml`: criterion → test mapping + start time + commit
     SHA.
5. **Execute tests in order.**
   - Unit first (`pytest backend/tests/<context> -q --junitxml=...`).
   - Integration next (same, integration dir).
   - E2E (`npx playwright test tests/e2e/<phase>/ --reporter=junit`).
   - Perf (`k6 run tests/perf/<phase>/<script>.js --summary-export=...`).
   - Capture stdout / stderr / exit-code / junit-xml / screenshots per
     run into the artefact dir.
6. **Apply flake heuristic.**
   - First-run fails AND test matches `agent-memory:verifier /
     flaky-tests` pattern → re-run **once**. Second run is the verdict.
   - Persistent flake → record in memory; verdict = fail with
     `reason: flaky-test`.
7. **Compose report.**
   - `verification-reports/<phase-id>/<rfc3339>/report.md` per
     `checklists/acceptance-run.md` output format.
8. **Emit verdict.**
   - All AC = PASS → `tech.oriion.phase.complete.v1` → memory-curator.
   - Any AC = FAIL → `tech.oriion.acceptance.failed.v1` → planner.
9. **Persist learning.**
   - New flake pattern → append.
   - Criteria template observed for phase-type → append.

## 2. Wave-transition gate verification (inbound: gate-file proposal)

**Trigger.** memory-curator drafts `.planning/gates/wave-N-to-N+1.md`
with `status: PENDING` + auto-filled `metrics_snapshot`. Verifier is
asked to confirm hard thresholds before founder is invited to flip
`status: PASSED`.

**Steps.**
1. **Read** the proposed gate-file frontmatter.
2. **Identify wave-pair** (e.g. `wave-1-to-2`). Load the corresponding
   measurement method from `checklists/gate-threshold-check.md`.
3. **Re-query each threshold from source.** Do **not** trust the
   pre-filled `actual` value. Run the measurement command (e.g. SQL
   against analytics DB, k6 against staging, scripted poll of
   product-metrics) and capture output into
   `verification-reports/gates/wave-N-to-N+1/<rfc3339>/`.
4. **Compare AND-combined.**
   - Single fail → emit `tech.oriion.acceptance.failed.v1` with
     `reason: gate-threshold-not-met`, payload lists each threshold +
     required + actual + verdict per row.
   - All pass → emit `tech.oriion.phase.complete.v1` with
     `subject: gate/wave-N-to-N+1`, payload includes the captured
     `actual` values. memory-curator updates frontmatter; founder
     applies narrative + `status: PASSED`.
5. **Never** flip `status` yourself. You emit verdict only.

## 3. Flaky-test investigation (inbound: planner asks for triage)

**Trigger.** A test failed in playbook 1, was re-run, second run also
failed; OR same test failed across ≥3 PRs in last 30 days. Planner
explicitly asks verifier to triage.

**Steps.**
1. Pull test history from memory namespace: last-N runs of this test ID.
2. Classify failure mode:
   - **True bug** — assertion matches actual product defect. Verdict:
     not-flake. Routes back to planner for implementer fix.
   - **Environmental flake** — timeout, network, race on fixture
     teardown. Append to `flaky-tests` collection with reproduction
     hints.
   - **Spec drift** — test asserts behaviour no longer required by
     PHASE.md. Verdict: spec-drift. Routes to planner to either update
     test or update spec (founder decides).
3. Write `verification-reports/<phase-id>/flake-investigation-<rfc3339>.md`
   with classification + evidence.
4. Emit `tech.oriion.acceptance.failed.v1` (or `phase.complete.v1` if
   investigation absolves) with explicit `reason` field.

**Hard rule.** Verifier never "fixes" a test to make it pass. Flake
classification is the contribution; the fix belongs to implementer or
planner.
