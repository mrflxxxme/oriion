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
### 2026-07-04T00:02:25Z | phase 01.7 | impl
- Fork: Permission source-of-truth for the RBAC guard: rbac.role_assignments (what AuthorizationService.has_permission reads) vs multitenancy.cell_members.role_id (what register/bootstrap actually populates)
- Decision: Enforce off cell_members.role_id. Add AuthorizationService.has_cell_permission joining multitenancy.cell_members -> rbac.role_permissions -> rbac.permissions for scope_type=cell. Leave has_permission (role_assignments path) intact for future workspace-scoped / delegated grants.
- Rationale: role_assignments is never written by app code or the SECURITY DEFINER bootstrap; only cell_members is populated (owner at register, editable via cells router). Backfilling role_assignments would duplicate the role store and risk drift. Option A is flat + cell-scoped, so cell_members is the correct authority. Smallest correct change.
- Reversibility: reversible

### 2026-07-04T00:02:30Z | phase 01.7 | impl
- Fork: Where to place the Owner-only enforcement guard (FastAPI dependency shape)
- Decision: New src/rbac/deps.py with require_cell_permission(slug) factory returning a FastAPI dependency; resolves current cell via the existing tenant_context (get_current_cell_id) + get_current_user, calls has_cell_permission, raises 403 PermissionDenied on miss. Apply to cells member-mgmt (invite/role-change/remove), cell-delete, and billing writes; Member keeps task-create + all reads.
- Rationale: Mirrors existing deps.py/Depends wiring (get_current_user, get_tenant_db_session). A permission-slug factory keeps call-sites declarative and avoids a per-endpoint bespoke check. 403 (not 404) because Option A = flat visibility: Members legitimately see the cell, they just lack the right.

### 2026-07-04T02:14:16Z | phase 01.8 | impl
- Fork: TOTP shared-secret at-rest storage: plaintext column vs. KMS-encrypted bytea vs. new dedicated crypto
- Decision: Encrypt with the existing KMSProvider (LocalAESKMS AES-256-GCM) into a totp_credentials.secret_encrypted bytea; decrypt in-memory only at verify/confirm; base32 plaintext leaves the service once (enroll response), never logged
- Rationale: Reuses the repo's established BYOK at-rest crypto (ADR-014 amendment); no new dependency; matches oauth_links.*_encrypted precedent; a sensitive secret must never sit plaintext at rest
- Reversibility: reversible

### 2026-07-04T02:14:16Z | phase 01.8 | impl
- Fork: Login second factor mechanism: single-call inline (password+code) vs. two-step challenge
- Decision: Two-step: /auth/login returns a short-lived HS256 TotpChallenge (type-guarded, 5-min, no server state) when 2FA active; /auth/login/totp exchanges challenge+code for a token pair; NO session minted on the password leg
- Rationale: Keeps the existing password-only /auth/login contract intact for non-2FA users; the signed short-lived challenge is un-forgeable + un-replayable without DB/Redis state; standard TOTP challenge-response UX
- Reversibility: reversible

### 2026-07-04T02:14:16Z | phase 01.8 | impl
- Fork: New iam auth tables RLS: cell-scoped RLS policy vs. user-scoped grant-only
- Decision: User-scoped, GRANT to oriion_app only, NO cell RLS policy (matches iam.sessions / email_verification_tokens / password_reset_tokens); authz enforced by user_id predicates in repos + get_current_user
- Rationale: These are pre-auth / identity-level rows keyed on user_id, not tenant cell_id; the iam context is system-level (schema.sql: 'RLS not applicable'); adding a cell policy would be wrong + break the pure-CREATE tripwire shape
- Reversibility: reversible

### 2026-07-08T21:54:23Z | phase run-2026-07-09 | impl
- Fork: Wave-1 phase ordering: D4 default queue (01.8c-first) vs product-must-set-first
- Decision: Reorder to product-first: 01.4-ui -> 01.9 -> 01.10 -> 01.12; 01.8c (dev-infra service phase) deferred to end/only-if-warranted
- Rationale: Founder run-args set explicit global goal = verifiably+fully complete Wave-1 PRODUCT, verified on VPS. 01.8c is not in the must-set and yields nothing server-verifiable. No hard dep (real independent audit subagents spawnable via Agent tool without 01.8c native-subagent files). Start with 01.4-ui: tripwire-free auto-merge, $0 live, server-verifiable -> validates full pipeline+deploy path before the hard/expensive 01.9. note#2 permits optimal ordering; note#6 'strictly follow workflow' governs merge/gate flow, not queue order.
- Reversibility: reversible

### 2026-07-08T21:56:27Z | phase 01.4-ui | impl
- Fork: Memory delete/mutate rights in UI: Owner-only vs any cell member
- Decision: Expose add+delete to any authenticated cell member (match live backend); confirm-dialog on delete
- Rationale: Live memory endpoints (backend/src/memory/routers/memory.py) are cell-scoped via RLS + get_current_workspace_id with NO Owner/Member guard — any cell member already can add/delete via API. UI must mirror live authz, not invent stricter rules. Memory is collaborative working context (byproduct of Member-allowed task-create), consistent with 01.7 pattern where reads+task-ops are Member-level. Reversible.
- Reversibility: reversible

### 2026-07-08T21:56:27Z | phase 01.4-ui | impl
- Fork: Edit semantics for memory entries (no PATCH endpoint exists)
- Decision: Edit = delete + re-add (append-only); no new backend endpoint
- Rationale: Router exposes only GET/POST/DELETE (no PATCH); backend memory is append-only by design (grill 2026-06-23). Adding PATCH is explicitly out-of-scope for 01.4-ui. delete+add preserves append-only + source provenance. Reversible.
- Reversibility: reversible

### 2026-07-08T23:15:43Z | phase 01.9 | arch
- Fork: 01.9 scope: single phase vs split (DLP-activation vs connectors)
- Decision: Split 01.9 -> 01.9a (DLP precision-tune INN FP<=1% + flip both security flags ON; closes DV-04/05; wave-gate-critical; autonomous) + 01.9b (3 read+draft connector tools + capability gate + KMS creds store + registry + mock tests; live-smoke deferred to RW-01/RW-03 creds)
- Rationale: DLP-activation is small, wave-gate-blocking (DV-04/05 = data-leak P1, blocks wave gate per DEFERRED-VERIFICATION protocol §3), fully autonomous+deterministically verifiable now, and tripwire-light (touches security/ + config, neither in tripwire) => likely auto-merge, lands the blocker fast+clean. Connectors are larger and their LIVE value is founder-cred-gated (RW-01 SMTP/IMAP, RW-03 Telegram) => build+mock now, live-smoke deferred (matches 01.8-mail pattern + seed 'dev-part autonomous with mocks'). Founder-preferred focused-split (infra-pr-scope memory). Reversible.
- Reversibility: reversible

### 2026-07-09T11:34:29Z | phase 01.9b | arch | ADR-041
- Fork: Connector integration mechanism: full MCP-protocol servers vs native-tool callables
- Decision: Native-tool callables (WebSearchTool/ReadURLTool pattern) + KMS creds-store + mcp.mcp_connections registry; real MCP-protocol transport deferred to Wave-2
- Rationale: 00.4 MCP client is a Wave-0 stub (empty connect(), no protocol); real tools reach pydantic-ai agents as native Agent(tools=[...]) callables. Wave-1 value = read+draft (grill), delivered identically by native tools at far lower cost/complexity vs building a full protocol layer + 3 server processes on a single-box VPS. MCP-protocol infra is Wave-2 (community/vertical connectors). Rubric: correctness+security tie, simplicity+cost decisively favor native. Judge-panel skipped (unambiguous winner, ADR-041 records the weighing). Reversible-ish (Wave-2 can add protocol transport on the same registry seam).
- Reversibility: reversible (registry + MCPClient stub are the forward seam for Wave-2 protocol)

### 2026-07-09T15:45:25Z | phase 01.10 | impl
- Fork: 01.10 evaluator: full 30-task judge-scored golden now vs lean live-golden + defer full cert to founder review-gate
- Decision: Lean live-golden 7/7 (plan+synthesis contract + 5 adversarial, ~$0.03) this PR; full 30-task golden≥75% certification + draft→reviewed promotion deferred to the founder review-gate (DV-12 + DV-02)
- Rationale: Prompts are draft (founder-reviewed per ADR-026 before reviewed); running the full judge-scored 30-task evaluator on draft prompts that may be revised = double-spend. Lean golden proves the Master-chain works on live LLM + adversarial-robust (the phase's core verification) at ~$0.03. Full certification + promotion is inherently a founder-gate step (note#5 defer founder-involvement) → runs when prompts finalized. Money-conscious (note#3). Reversible.
- Reversibility: reversible

### 2026-07-09T20:33:57Z | phase 01.8c | impl
- Fork: 01.8c decomposition: bundle 5 scope items in one PR vs split rename out
- Decision: Split into PR-1 (items 1,2,3,5 = subagents + openapi-CI + docs-freshness-CI + JOURNAL archival) and PR-2 (item 4 = Oriion rename)
- Rationale: Reviewability: the 63-file rename is pure string-noise that would bury substantive review of subagent defs + CI logic; decoupling protects high-value infra from rename/iam-touch risk; matches founder pref for focused splits (memory infra-pr-scope-prefers-focused-splits). Both PRs this run, merges serialized w/ health-check.
- Reversibility: reversible

### 2026-07-09T20:33:57Z | phase 01.8c | impl
- Fork: teamly->Oriion rename scope: literal grep=0 everywhere vs active-surface only
- Decision: Rename Oriion across active code + config + instructions + user-facing strings + role-prompts (SemVer bump); PRESERVE immutable historical records (ADR bodies, dated AUDIT-*, JOURNAL history) + external memory-file-name ref in test_worker_sse_lifecycle.py
- Rationale: ADR-040 D3: Oriion is the working name everywhere incl user-facing (OQ-09 final brand still open = future one-op swap), so already-decided/agent-owned, not a product escalation. Rewriting append-only historical records corrupts audit trail (00-START-HERE: old docs keep TEAMLY_RU as factual). AC refined to active-surface.
- Reversibility: reversible

### 2026-07-09T20:33:57Z | phase 01.8c | impl
- Fork: Native subagent file shape (.claude/agents/<role>.md)
- Decision: Claude Code subagent frontmatter (name/description/tools/model) synthesized from profile.md (name, model_tier->model, mandate->description) + tools-allowlist.md (tools) + system-prompt.md (body); role dir handbooks preserved as reference
- Rationale: Reuses the existing rich role artifacts verbatim; model_tier maps opus->opus w/ tier_fallback roles->sonnet per cost-budget; file+dir coexist (stem vs dir). Closes ADR-037/D8 known gap so judge-panel + reviewer lenses spawn real isolated-context subagents.
- Reversibility: reversible

### 2026-07-09T20:33:57Z | phase 01.8c | impl
- Fork: OpenAPI snapshot export tooling (D2)
- Decision: Small script imports src.main:app, dumps app.openapi() to .planning/contracts/openapi.snapshot.json (sorted keys, stable format); CI job regenerates + git-diff --exit-code, breaking-diff = red + tripwire signal
- Rationale: FastAPI native app.openapi() is the source of truth for the live contract (D2); deterministic sorted dump makes diff meaningful; no new deps.
- Reversibility: reversible

### 2026-07-09T20:33:58Z | phase 01.8c | impl
- Fork: Docs-freshness CI mechanism (D9)
- Decision: Python check: any phase spec-file whose slug is marked merged/complete in STATUS.md but still has 'Status: Pending' in its own spec = red; plus README 'текущая фаза' cross-checked vs STATUS.md active phase
- Rationale: Directly implements D9 acceptance ('merged phase with Status Pending = red'); lightweight, stdlib-only, no external services.
- Reversibility: reversible

### 2026-07-11 | wave-2 planning | product/founder-grill (grill-2026-07-11)

> Сессия планирования Wave 2 (ADR-040 D6): founder-grill 24 решения + фоновый аудит (backend/frontend/canon — все W1-гейты green, блокеров нет). Каждое решение — founder-verdict после анализа+рекомендации. Материализовано этой же сессией: PHASES.md + README W2 + 13 seed-specs + gate wave-2-to-3 rewrite + ADR-042 + amendments ADR-004/007/013/021/030/041 + RW-10/RW-11 + DV-13 + docs-sync канона.

- D-01 Deliverable сессии: seed-specs + предрешённые форки (не полные спеки — JIT per ADR-040 D1)
- D-02 Цель волны: public beta С монетизацией; 01.3b в треке parked-until-RW-04; RW-04 стартует неделя 1; «50 платящих» = замер, не гейт
- D-03 Mini App → W3 (связка с 01.11 Business API, RW-05); approval-поверхность W2 = веб
- D-04 MCP-протокол → W3; W2 = native-tools only (amendment ADR-041/013)
- D-05 Порядок волны: цикл ценности → вертикали → упаковка → платежи → инфра-хвосты
- D-06 WB-Селлер УДАЛЁН целиком (вертикаль+коннектор+герой+пресет+golden); verticals/wb-seller → retired-архив
- D-07 Без новой вертикали в W2; выбор следующей — гейт W2→3 по данным 02.0/беты
- D-08 Approval-UI: human-approved send TG-пост+email; fail-closed scoping в скоуп; layer-A ML deferred до autonomous-send (W3+); autonomous send OFF
- D-09 Pixel-ассеты: API-генерация агентами + founder-курация (amendment ADR-021; ComfyUI/GPU-трек отменён)
- D-10 Гейт волны по Pixel: скин live + 24 AI-архетипа; hand-drawn герои (2: Анастасия, Денис) — asset-апдейт ВНЕ гейта (R-14 снят с критического пути)
- D-11 Платёжная модель: рекуррентная подписка ЮKassa + разовые credit-паки
- D-12 Прод-домен: профики.online (корень = лендинги Astro, app. = приложение)
- D-13 02.0 инструменты: событийная воронка из БД + in-app NPS-виджет (0-10 + текст); сторонняя аналитика — решение на гейте
- D-14 Pyodide UX: код-артефакт + явная кнопка Run (не авто-исполнение; интерактивный ноутбук — W3-кандидат)
- D-15 RBAC: Admin + Viewer + DV-07 enforcement; Bot/Service → W3
- D-16 Auth: остаёмся custom JWT email-only; amendment ADR-007 (триггер пересмотра = enterprise SSO спрос); Logto-миграция снята с W2-3
- D-17 Гейт W2→3: hard = вычислимые технические пороги; регистрации/TTFV/конверсия/платящие/NPS = замеры (решение founder)
- D-18 Timebox: ~8 недель, ориентир 2026-09-07 (ориентир, не жёсткий дедлайн)
- D-19 Бюджет: капы v4 без изменений ($50 soft / $75 hard/день)
- D-20 Pixel-скин: ПОЛНЫЙ скин-режим UI (data-skin ось: радиусы/шрифты/акценты), не только аватары
- D-21 Спрайты живут по live SSE-состояниям задач уже в W2 (idle/working/success; +thinking/error у героев)
- D-22 Офис-вью: секция на странице ячейки + мини-виджет на Dashboard (без отдельного роута)
- D-23 Пиксель-тур: опциональный шаг onboarding-wizard; вливается с 02.7 (когда спрайты существуют)
- D-24 НОВАЯ ФАЗА 02.2 tier-1 редизайн сразу после retro: фундаментальный UX-research трендов → пересборка IA/навигации/лейаутов + DS v0.3; founder готов уделять время (4 touchpoints: бриф → IA → bake-off → утверждение); ADR-042
- Reversibility: продуктовые решения reversible новым grill-verdict; D-06 (удаление WB) — reversible (архив сохранён); D-24 (редизайн) — hard-to-reverse после материализации DS v0.3

### 2026-07-11 | wave-2 planning (grill-доп) | product/founder-grill — D-25..D-28 СУПЕРСИД D-03/D-04

> Founder: «раз убрали WB — вернём последними фазами Mini App и MCP-протокол». Дополнительное интервью 4 вопроса; все — по рекомендации.

- D-25 Mini App ВОЗВРАЩЁН в W2 фазой 02.12 (суперсид D-03): скоуп БЕЗ Business API — мобильный approval-фронт (reuse API 02.3) + задачи/артефакты + нотификации; auth = initData-обмен; 01.11 остаётся parked RW-05, DM-сценарии — апгрейдом; security review обязателен
- D-26 MCP-протокол ВОЗВРАЩЁН замыкающей фазой 02.13 (суперсид D-04): реальный клиент (stdio/streamable-http) + каталог интеграций UI + community-серверы **github-mcp + google-sheets-mcp** (notion/slack/gmail/gdrive → W3); наши коннекторы остаются native (ADR-041); unknown-tool fail-closed
- D-27 Порядок финала: 02.12 Mini App → 02.13 MCP; 02.13 = ПЕРВЫЙ кандидат на документированный перенос в W3 при затягивании волны (аналог протокола RUNWAY №3)
- D-28 Гейт: +2 hard-порога (mini_app_live, mcp_live — второй условный per D-27); ориентир волны 2026-09-07 → **2026-09-21** (+2 нед на возвращённые фазы)
- Reversibility: reversible (перенос назад в W3 — штатный путь D-27)
