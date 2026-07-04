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

### 2026-07-03T15:09:47Z | phase 01.8 | impl
- Fork: 01.8 auth split + real SMTP sender placement
- Decision: Split: 01.8 core = 2FA TOTP (pyotp) + magic-link (on existing EmailSender port, InMemory-tested) + session-list backend, fully autonomous; 01.8b = Yandex ID + VK ID OAuth (needs client creds). Real YandexSmtpEmailSender = EARLY dedicated slot 01.8-mail (pre-alpha prerequisite), before OAuth: runner writes impl + transport-mock tests autonomously, live-send validates when SMTP creds land in the canonical .env
- Rationale: founder grill verdict 2026-07-03 (Option A + split): email verification is mandatory before first task (ADR-007) but prod sender is NoOp today - friends cannot self-verify => SMTP is a pre-alpha launch blocker independent of auth-extensions; must NOT be coupled to OAuth-app-registration timing. Split maximizes autonomous volume (OAuth is the only piece needing external client creds). Robust to cred timing: code+mock now, live-send is the follow-up gate.
- Reversibility: reversible

### 2026-07-03T15:24:16Z | phase 01.7 | impl
- Fork: RBAC Member artifact-visibility granularity (Wave-1)
- Decision: Option A: flat - all cell members see all cell artifacts (RLS already by cell_id; Member = cell access). Owner vs Member differ only in RIGHTS (Owner: billing + management + cell-delete; Member: create tasks, see everything in cell), NOT content visibility. Stub only: add visibility text DEFAULT 'cell-shared' to the artifacts envelope (added in 01.7's migration, fast-default, no backfill), NOT enforced - enables per-artifact privacy (B) later without an ALTER-under-data
- Rationale: founder grill verdict 2026-07-03: pre-alpha cells are single-user; even with Member, a friends-team works on shared artifacts - hiding them prematurely is friction. Per-artifact privacy (B) + agent-whitelist (C) are Wave-2+ granularity when real teams need separation. Substrate-field-now / enforce-later (same pattern as quotas).
- Reversibility: reversible

### 2026-07-03T15:29:08Z | phase 01.9 | impl
- Fork: MCP outward-action default before approval-UI exists + server scope
- Decision: Option A: Wave-1 connectors are READ + DRAFT only - read/fetch (Disk files, TG posts, IMAP inbox) + agent prepares a draft (message/email as an artifact); autonomous outward SEND (send_email/send_telegram) is DENY-until-approval-UI (01.12). Scope = all three servers (telegram-mcp Bot-API + yandex-disk-mcp + imap-smtp-mcp) but each read+draft only, no exotic features. Cross-ref: activates the capability-gate seam from 01.6; constrains 01.11 (TG Business send also gated)
- Rationale: founder grill verdict 2026-07-03: autonomous send-as-user without a single confirmation (B) = reputational + 152-FZ risk on an unproven product (one hallucinated client email = platform-wide trust loss); DLP catches PII but not 'agent wrote nonsense and sent it'. Read+Draft delivers 90pct value (agent gathers context + drafts), human sends, until 01.12 approval-flow turns on autonomous send deliberately. C (config-flag without UI) rejected as a footgun even opt-in.
- Reversibility: reversible

### 2026-07-03T15:36:30Z | phase 01.10 | impl
- Fork: Vertical-prompt authorship process under the autonomous runner (pattern for ALL verticals)
- Decision: Option B (autonomous-draft -> founder review-gate) ENHANCED with a mandatory research-first phase. Pipeline: (1) DOMAIN RESEARCH phase - a researcher-role agent (WebSearch/WebFetch + funded Brave/Yandex search) produces an internal market/domain brief for the vertical: target audience (CA), behavioral patterns, key content types + tone, competitor conventions, pain points, success criteria - grounded + cited; (2) DRAFT AUTHORING grounded in that brief (not thin general knowledge), optionally judge-panel N-variants; (3) golden dataset + evaluator scoring; (4) REVIEW-GATE = founder promotes draft->reviewed, with the research brief travelling in the PR so the founder reviews the GROUNDING too. Amend ADR-026 (vertical-expertise-pipeline) with the research-first step at 01.10 start
- Rationale: founder grill verdict 2026-07-03: B + internal preliminary market research so agents understand the vertical's specifics (behavioral pattern + key aspects) and prompts come out higher quality. Founder's market knowledge enters at review (targeted, fast) not per-prompt authorship - the pattern we are moving TO. Research-first raises first-draft quality so promotion is more often a rubber-stamp; cost of the research phase is repaid in fewer founder edit cycles. C (1-2 line positioning skeleton upfront) stays fallback for truly niche verticals (IP-buh, WB-seller W2/W3).
- Reversibility: reversible

### 2026-07-03T15:41:07Z | phase 01.11 | impl
- Fork: How the runner treats a legally-gated phase (OQ-32/OQ-33)
- Decision: Option B: runner builds the FULL flagged scaffold autonomously behind feature_flag=OFF (Business-API integration, consent model, per-DM-access audit logging, ephemeral <=7d retention, pgcrypto encryption) - all mock/fixture-tested, ZERO live calls to real private DMs, flag stays OFF. Legal closure of OQ-32/33 = review of ready code + flag flip + RKN notification, not a from-scratch start. HARD RULE: any code that ACTIVATES real DM reads OR flips the flag -> escalate (tripwire secrets + product 152-FZ)
- Rationale: founder grill verdict 2026-07-03: the legal gate is about ACTIVATION of PDN processing, not the existence of code. Runner can safely build the whole integration behind an off flag (exactly what ADR-030 prescribes), maximizing autonomous volume even on a gated phase. A (wait entirely) loses weeks of autonomous work on code that is legally writable now. C is a half-measure - the scaffold already covers the consent-UX model.
- Reversibility: reversible

### 2026-07-03T15:48:10Z | phase 01.12 | impl
- Fork: Staying autonomous on the product-heavy Dashboard/Onboarding phase
- Decision: Principle (also amends escalation-policy D4): user-facing content ALREADY specified in an ADR/UI-SPEC (wizard copy in ADR-022, product units in ADR-016, palette in ADR-031) is IMPLEMENTED as-is, NOT re-escalated - executing an approved spec is not a new product decision. Demo-scenarios / seeded first-task examples (not in any ADR) -> autonomous research-first draft + founder review-gate (same as vertical prompts). Net-new user-facing decisions covered by NO ADR -> escalate. 01.12 thus near-autonomous: wizard/dashboard/approval-UI per ADR-022/016/031, demo-scenarios via draft->review-gate
- Rationale: founder grill verdict 2026-07-03: resolves the tension 'frontend is outside the tripwire but user-facing escalates per D4' - what escalates is not everything VISIBLE but everything UNDECIDED-and-visible. Same rule cuts escalations across all future UI phases.
- Reversibility: reversible

### 2026-07-03T16:19:56Z | phase 01.5 | impl
- Fork: Loosen db_migrations tripwire for greenfield without weakening the gate
- Decision: Option C (grill): classify_tripwire v2 content-inspects upgrade() and auto-drops db_migrations iff EVERY touched migration is a provable pure-CREATE; fail-closed on any f-string/ALTER/DROP/backfill/index-on-existing/unknown-call/unreadable. Complexity kept OUT of the gate: new cell-scoped migrations use literal-arg helpers backend/migrations/_rls.py (cell_scoped_rls/updated_at_trigger) instead of the f-string RLS loop, so the classifier stays a simple strip-strings + call-allow-list. Shipped PR #82
- Rationale: founder grill verdict 2026-07-03 (chose C after a grounded finding): the house RLS idiom is an un-provable f-string loop; teaching the GATE to prove loop domains puts a fragile parser where a miss = an unattended destructive migration auto-merging. C moves that complexity into an ordinary tested helper and keeps the safety-critical gate dumb + statically verifiable. A (conservative-only) was near-worthless since the house writes no literal migrations; B (smart parser in gate) too risky.
- Reversibility: reversible

### 2026-07-03T16:50:56Z | phase 01.6 | arch | ADR-039
- Fork: Formalize the grill-resolved security-guardrails architecture into an ADR
- Decision: ADR-039 Accepted: new 'security' bounded context with detector PORTS + deterministic layer B (regex+checksum RU-PDN; injection heuristics); NO tables/migrations (DLP writes existing audit.audit_log); runtime seams mirror quota_admission/memory_extraction; port seam preserves B->A ML upgrade
- Rationale: Gril 2026-07-03 pre-resolved the arch fork (14:09 entry); the runner authors the ADR per the 'own ADR at 01.6 start' instruction. Zero-migration keeps the blocking gate deterministic + Docker-independent (no stuck-risk) + tripwire-free (auto-merge)
- Reversibility: arch: reversible via port swap (B->A); bounded-context boundary is durable

### 2026-07-03T16:51:08Z | phase 01.6 | impl
- Fork: Capability risk_level metadata: grill assumed it exists on agents.roles
- Decision: Implement tool risk as a deterministic STATIC registry (TOOL_RISK dict in src/security/capability.py) + classify_tool()/requires_approval() (fail-closed: unknown->dangerous), NOT a DB column
- Rationale: Recon found there is NO agents.roles table (personas live in agents.agent_archetypes with tools_allowed ARRAY) and NO risk_level column. A static registry satisfies the grill intent ('classify tools by risk + seam, no gate') with ZERO migration - even more aligned with the deterministic/no-stuck-risk goal than an ALTER. Real gate still activates 01.9.
- Reversibility: reversible; a DB-backed per-workspace override can layer on in 01.9 owner-config

### 2026-07-03T16:51:08Z | phase 01.6 | impl
- Fork: Guardrail enforcement default-state in Wave-1 (dlp + injection flags)
- Decision: security_injection_scan_enabled default TRUE (B1 non-destructive, no-op on benign, protects the only external channel = web results); security_dlp_enabled default FALSE (A3 hard-block, activates at first outward PII surface = 01.9 + owner-config). Both behaviors fully built + unit-tested; activation = flag flip
- Rationale: Mirrors the founder's uniform 'substrate-now, enforce-when-there-is-a-surface' pattern applied to EVERY sibling 01.6 fork (capability gate->01.9; storage quotas->W2; co-editing->W2). DLP hard-block has false-positive friction (legit marketing brief with a client phone) and NO outward PII surface exists in Wave-1 (artifacts cell-scoped under RLS; connectors=01.9). 'Before any PII surface' = the gate must EXIST before 01.9, satisfied by building it now. Injection B1 is safe to enable (non-destructive).
- Reversibility: reversible; single-line flag flip in 01.9

### 2026-07-03T17:28:18Z | phase 01.6 | impl
- Fork: Adversarial-audit corrections (3 lenses, refute-by-default)
- Decision: SOUND P1: DLP screens the FULL outward deliverable (_dlp_screen_text = json.dumps(model_dump()), uncapped) not the truncated memory-filter _deliverable_text, so screened >= delivered. NO-REG P2: security_injection_scan_enabled default flipped True->False (heuristics mangle legit web content quoting an attack / LLM-template markers; thesis 'no-op on benign' refuted) + trimmed jailbreak_marker (drop bare developer-mode/jailbreak) + fenced_system_block (drop markdown-heading branch). P3: DLP block except broadened to Exception (a screen/audit-DB failure now stamps task.failed instead of leaving 'running'). SECURE PASS (0 P0/P1).
- Rationale: Fix soundness + the regression + cheap robustness now; DEFER the INN-10 ~10%-false-positive precision-tuning to 01.9 activation (real-data validation belongs at flip time, not blind now) with an explicit must-do note in the phase spec. Both guardrail flags now default OFF (substrate-now, enforce-at-01.9) — consistent with the capability-gate decision for this same phase.
- Reversibility: reversible; flags + patterns tunable at 01.9

### 2026-07-04T01:05:50Z | phase 01.8-mail | impl
- Fork: SMTP TLS default: implicit-TLS 465 vs STARTTLS 587 as the Settings default
- Decision: smtp_port=465 + smtp_use_tls=True (implicit TLS) as default; STARTTLS 587 supported via smtp_use_tls=False. STARTTLS path sets aiosmtplib start_tls=True so AUTH never crosses cleartext.
- Rationale: Yandex 360 recommends 465 implicit-TLS; simplest secure default (SSL-on-connect, no downgrade window). Both modes enforce TLS-before-AUTH; cert-verify left at ssl default (never disabled).
- Reversibility: reversible
- Session: claude/auto-01.8-mail
