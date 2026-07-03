# Autonomy decisions-log

> Append-only. Every agent-owned fork the autonomous runner resolved without asking the founder (ADR-037 D4). The founder's post-hoc audit trail. Architectural entries also have an ADR (see `ADR-refs`). Written by `scripts/autonomy/log_decision.py`.

### 2026-07-01T22:18:59Z | phase 01.5 | impl
- Fork: Migrations+RLS shape for new artifacts tables
- Decision: Own migration branch dir backend/migrations/versions/artifacts/ + single 'artifacts' schema + FORCE RLS via current_setting('app.current_cell_id') house pattern (as memory 01.4 did)
- Rationale: House pattern proven in memory/billing contexts; no new pattern invented; tripwire db_migrations still applies at merge
- Reversibility: reversible

### 2026-07-01T22:18:59Z | phase 01.5 | impl
- Fork: S3 client + env seam
- Decision: boto3 (already a declared dep) against MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY env (already wired in infra/docker-compose.dev.yml); presigned POST upload 5-min TTL + signed GET 1h TTL per ADR-012
- Rationale: ADR-012 fixes the flow; dev compose already ships MinIO; no new dependency
- Reversibility: reversible

### 2026-07-01T22:18:59Z | phase 01.5 | impl
- Fork: Search (full-text/vector/facets) in 01.5 or not
- Decision: NOT in 01.5 - basic list/filter endpoints only; GIN/pgvector search deferred until a consumer exists
- Rationale: Phase one-liner (PHASES.md) scopes 01.5 to Yjs docs + S3 assets + artifact:// URLs; vector search needs live embedding API (funded .env absent) and has no Wave-1 consumer; R-12 scope-creep guard; schema must not preclude later search
- Reversibility: reversible

### 2026-07-01T22:19:35Z | phase 01.5 | impl
- Fork: API surface shape
- Decision: Follow contract skeleton paths under /api/v1/artifacts/* (yjs/{document_id}, yjs/{id}/snapshots, s3/upload-url, s3/{asset_id}); fill .planning/contracts/artifacts placeholders to match implementation
- Rationale: Skeleton paths already cross-referenced by other contexts; filling placeholders is the phase's contract deliverable per ADR-024; contracts change trips public_api_contracts tripwire at merge as expected
- Reversibility: reversible

### 2026-07-01T22:19:35Z | phase 01.5 | impl
- Fork: Integration test harness for S3
- Decision: Reuse existing real-PG integration harness; S3 tests against MinIO from infra/docker-compose.dev.yml (Docker confirmed up); unit tests mock the S3 port
- Rationale: House pattern: integration = real backing services; MinIO already provisioned; no testcontainers addition needed unless harness dictates otherwise at execution
- Reversibility: reversible

### 2026-07-01T22:20:25Z | phase 01.5 | escalated
- Fork: Co-editing scope: y-websocket in 01.5 or defer
- Decision: ESCALATED to founder (RQ-20260701-001); proceeding on lean B (REST-only Yjs persistence) as non-blocking substrate
- Rationale: Wave-scope = product per D4; lean B identical storage layer under both options
- Reversibility: reversible

### 2026-07-01T22:20:37Z | phase 01.5 | escalated
- Fork: Storage quota enforcement per tariff
- Decision: ESCALATED to founder (RQ-20260701-002); proceeding on lean B (track-only per-cell byte usage) as non-blocking substrate
- Rationale: Commercial term = product per D4 + billing tripwire adjacency; tracking substrate serves both options
- Reversibility: reversible

### 2026-07-01T22:33:19Z | phase 01.5 | arch | ADR-038
- Fork: Artifacts schema: envelope (ADR-012 sketch) vs flat (contract skeleton) + Yjs persistence format/library
- Decision: Envelope model in single 'artifacts' schema, G1 winner + 6 grafts (current_version_num, s3_objects lifecycle table, composite anti-drift FKs, text_export, 404-no-oracle, storage_kind evolution comment); bytea + pycrdt synchronous merge under FOR UPDATE
- Rationale: Judge-panel N=3 (ADR-faithful/flat/evolution) + evaluator, lexicographic rubric. Correctness gate ordered G1(8) > G2(7) > G3(6): G3 broke read-your-writes (async merge), G2 rebound artifact:// grammar onto two probabilistic ID namespaces and dropped ADR-012 tags/type/'code'. Full verdict in ADR-038
- Reversibility: hard-to-reverse (schema, public-ish seam)

### 2026-07-03T12:33:35Z | phase 01.5 | impl
- Fork: ci-evidence freshness circularity: evidence commit advances the tip so head_sha==tip is unsatisfiable once a manifest exists
- Decision: verify_evidence.py walks first-parent past commits touching ONLY evidence/ (bounded, 5); ci-evidence checkout fetch-depth 25; 3 tooling tests incl. mixed-commit stays stale
- Rationale: Hash circularity: a commit cannot contain its own sha. Freshness redefined as no non-evidence commit after the gate - teeth preserved (any code/docs path stales). 01.5 is the first manifest consumer; without the fix ci-evidence is permanently red
- Reversibility: reversible

### 2026-07-03T13:39:19Z | phase 01.5 | impl
- Fork: Heal root-cause: red main after PR #78 squash
- Decision: Forward-fix without revert: PR #79 (gitleaks squash-sha fingerprint + ci-evidence PR-only + evidence/ cleanup) + PR #80 (health-check ignores PR-only workflows' stale main runs)
- Rationale: ci-backend green = no code regression; both red legs were squash-semantics false positives of gate bookkeeping; revert provably cannot cure a history-scan finding. Gate gap closed with 7 new tooling tests
- Reversibility: reversible

### 2026-07-03T14:00:18Z | phase 01.5 | escalated
- Fork: Co-editing scope: y-websocket real-time sync now or defer
- Decision: DEFERRED to Wave 2 (Option C) - new phase 02.9; REST-only Yjs persistence is the Wave-1 substrate
- Rationale: founder verdict (grill): pre-alpha cells are single-user (multitenancy single-cell, RBAC Member=01.7, first editable surface=01.12); no co-editing consumer exists in Wave 1; ADR-038 substrate reuses state+state_vector+update-log with zero schema change
- Reversibility: reversible

### 2026-07-03T14:04:26Z | phase 01.5 | escalated
- Fork: Storage quota enforcement per tariff: now or defer, hard vs soft
- Decision: DEFER enforcement to Wave 2 (phase 02.10); HARD-REJECT semantics on upload admission; 01.5 cell_storage_usage tracking is the substrate
- Rationale: founder verdict (grill): pre-alpha friends will not hit 1GB; premature enforcement = friction on an unproven path. Storage is hard-reject (not billing-style soft-warn) - out of space means out of space; runaway guard R-04 also favors hard. 90pct alert cheap, bundled with enforcement phase.
- Reversibility: reversible

### 2026-07-03T14:09:24Z | phase 01.6 | arch
- Fork: Guardrails detection approach + bounded-context placement
- Decision: New 'security' bounded context (own ADR at 01.6 start) with detector PORTS; Wave-1 impl = deterministic layer B (regex/dictionary for RU-PDN INN/SNILS/passport/phone with checksum validation; injection = heuristics + known patterns); port seam lets B->A (Prompt Guard/bge ML models) swap later with zero call-site change
- Rationale: founder grill verdict 2026-07-03: 01.6 is a BLOCKING gate ('before any PII surface') - must not carry a model-serving/funded-download stuck-risk. RU-PDN is deterministically catchable with checksums (regex's strength, explainable for security review). Injection risk is low in Wave-1 (no external connectors until 01.9). LLM-as-judge rejected (per-call cost/latency + funded-key dependency for a near-absent pre-alpha scenario). Port seam preserves the A upgrade path.
- Reversibility: arch: reversible via port swap (B->A); bounded-context boundary is the durable part

### 2026-07-03T14:20:53Z | phase 01.6 | impl
- Fork: Guardrail trigger behavior: output-DLP vs input-injection (product)
- Decision: Wave-1: (a) output DLP = A3 hard-block + audit-log row + explicit task error (NO interactive approval - approval-UI is 01.12, layers onto the same seam later); (b) input injection = B1 strip/neutralize the flagged fragment + continue with a note (not block-all-content)
- Rationale: founder grill verdict 2026-07-03: interactive approval (A1) impossible without UI (01.12) - a blocking security phase cannot depend on a far UI phase; masking output (A2) rejected (silently altering agent content is worse than an honest stop). Input B1 over B2: one injected fragment in a web page must not kill the whole legitimate task; strip+note preserves useful work. Masking/Approval-mode-per-role stays Wave-3 per ADR-014.
- Reversibility: reversible

### 2026-07-03T14:33:15Z | phase 01.6 | impl
- Fork: Capability sandboxing scope for Wave-1
- Decision: Option B: classify tools by risk_level (metadata exists on agents.roles) + enforcement-SEAM (same port pattern as detectors), but NO actual capability-gate in 01.6. The real gate activates in 01.9 when the first dangerous connectors land, together with the owner-config surface
- Rationale: founder grill verdict 2026-07-03: Wave-1 agents have no outward action-tools (send_email/telegram/money = 01.9+ connectors; web_search/read_url read-only). Hard-deny (A) or approval-flow (C) now = enforcement for a non-existent surface. Substrate-now / enforce-when-there-is-something-to-enforce (same principle as co-editing + quotas). Cross-ref: 01.9 activates the gate.
- Reversibility: reversible
