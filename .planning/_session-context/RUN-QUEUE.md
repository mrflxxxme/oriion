# RUN-QUEUE — autonomous runner interrupt queue

> Append-only log of runner interrupt events (ADR-037 D8): ack-needed / escalation / revert / stuck / complete. Pending entries are waiting for the founder; resolve with `/autonomy:ack <ID> <verdict>`. Written by `scripts/autonomy/run_queue.py`.

### RQ-20260701-001 | escalation | pr:- | phase:01.5 | 2026-07-01T22:19:35Z | status:pending
- Summary: Co-editing scope: y-websocket real-time sync server in 01.5 or defer
- Fork: does 01.5 ship the real-time co-editing sync layer, or REST-only Yjs persistence? Options: A) full y-websocket sync server now B) REST-only Yjs snapshot/update persistence now, real-time sync deferred until a co-editing UI exists (01.12+/Wave 2). Agent's lean: B - no Wave-1 UI surface can co-edit; storage layer is identical under both; y-websocket adds an infra component with zero consumers now; ADR-012 already fixes Yjs as the document substrate so B precludes nothing. Why escalated: which feature is in-scope for a wave = product/market per escalation-policy D4. Blocks: NOTHING in this PR (B is the substrate for A); ack determines whether a follow-up sync-server phase is queued. Resolve: /autonomy:ack <ID> approved (=B) or revise <ID> <note>.
- Resolve: `/autonomy:ack RQ-20260701-001 approved|rejected`

### RQ-20260701-002 | escalation | pr:- | phase:01.5 | 2026-07-01T22:20:25Z | status:pending
- Summary: Storage quotas per tariff: enforce at upload in 01.5 or track-only
- Fork: ADR-012 defines per-tariff storage limits (Trial 1GB / Solo 5GB / Team 10-200GB). Enforce now or defer? Options: A) enforce caps at upload admission in 01.5 incl. breach UX (reject vs warn) - touches billing surface B) track per-cell byte usage in artifacts context now (cheap aggregate), enforcement + breach UX in a billing follow-up phase. Agent's lean: B - enforcement semantics are a user-visible commercial term (founder domain) and touch the billing tripwire surface; usage tracking is the substrate either way. Why escalated: pricing/tariff commercial term per escalation-policy D4 + billing tripwire adjacency at design step. Blocks: NOTHING in this PR. Resolve: /autonomy:ack <ID> approved (=B) or revise <ID> <note>.
- Resolve: `/autonomy:ack RQ-20260701-002 approved|rejected`

### RQ-20260703-001 | stuck | pr:- | phase:01.5 | 2026-07-03T12:23:14Z | status:resolved | resolved:2026-07-03T12:28:55Z | verdict:approved
- Resolution note: Docker restored by founder; runner resumed (integration re-run in flight)
- Summary: Docker Desktop is down - integration gate blocked mid-phase
- State: all code + audit fixes committed on claude/auto-01.5-artifacts (HEAD a04faf3). Static gates GREEN on final code (ruff clean, mypy --strict 214 files, bandit 0, unit 849 passed incl. new concurrency test). Integration gate (real PG + MinIO, 55 tests incl. 9 artifacts) last ran green BEFORE the audit-fix commits - evidence freshness (head_sha == final commit) requires a re-run. Docker Desktop is founder-controlled; runner will not start it. ACTION: start Docker Desktop (PG + MinIO from infra/docker-compose.dev.yml) - the runner resumes automatically: re-run integration -> emit evidence -> exit ritual -> PR -> tripwire classify (expected ack: db_migrations + public_api_contracts).

### RQ-20260703-002 | ack-needed | pr:78 | phase:01.5 | 2026-07-03T12:47:06Z | status:pending
- Summary: PR #78 (01.5 Artefakty) green + evidence fresh - tripwire ack required before merge
- Categories: db_migrations (backend/migrations/versions/artifacts/0001_artifacts_core.py - runner nuance verdict: PURE GREENFIELD - CREATE new 'artifacts' schema + 7 new tables + their RLS from scratch; ZERO ALTER/DROP of existing tables, zero RLS changes on existing tables, no backfill - low risk, v1 policy still requires ack) + public_api_contracts (.planning/contracts/artifacts/* - SKELETON placeholders rewritten to match the implementation, the phase's contract deliverable per ADR-024; no existing consumer contract broken). Gates: local ruff/mypy-strict-214/bandit-0/unit-852/integration-55(real PG+MinIO)/coverage-93пpercent; evidence 3 gates fresh+PASS at ea5208f; adversarial audit 3 lenses closed (1 P1 fixed with race test). CI checks on PR #78 being watched. Resolve: /autonomy:ack <this-ID> approved -> runner merges (squash).
- Resolve: `/autonomy:ack RQ-20260703-002 approved|rejected`
