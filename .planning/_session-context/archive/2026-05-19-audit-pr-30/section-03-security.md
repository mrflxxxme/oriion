# Audit Section 3 — Security Engineer

**Auditor:** Security Engineer subagent
**Date:** 2026-05-19
**Scope:** Phase 00.3 + 00.4 combined PR — security surface (RLS, KMS/BYOK, SSRF, secrets, OWASP, audit log)
**Branch:** `claude/cool-bell-0c74ba`
**Commits reviewed:** `f5d3e56..a3f54bf` (Phase 00.3 + 00.4 stack, 8 commits)

---

## Verdict

**FLAG** — no critical block-the-PR vulnerabilities, but **three High-severity findings** must be addressed before Phase 00.2.5 wiring lands (when GUC-bind happens on the real request path). Wave 0 ships service-layer + migrations + 501 routers, so the exploitable surface is limited; however the policy-correctness defects identified here will silently mis-fail (raise exception vs deny rows) the moment 00.2.5 wires real handlers.

---

## Threat-model summary

The PR introduces the **3-GUC layered RLS model** (`app.current_user_id`, `app.current_workspace_id`, `app.current_cell_id`) backing default-deny tenant isolation across `multitenancy.*`, `rbac.role_assignments`, `llm_gateway.byok_keys`, `llm_gateway.llm_usage_log`, `billing.credit_transactions`, and `mcp.mcp_connections`. The trust boundary is the FastAPI request handler → SQLAlchemy `AsyncSession` transaction; `set_tenant_context` (`backend/src/_shared/db/rls.py:37`) binds the three GUCs via `SET LOCAL`, and every multi-tenant table has `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` so even the table owner (oriion_app) is subject to policies.

The **BYOK custody chain** uses AES-256-GCM (`LocalAESKMS`, `backend/src/llm_gateway/services/kms_provider.py:50`) with 12-byte nonces from `secrets.token_bytes`, master key from `BYOK_MASTER_KEY_B64` (32-byte b64), and a clean encrypt-on-store / decrypt-on-demand contract. Plaintext keys are never logged, never echoed in API responses, and the API schema (`BYOKKeyOut`) only surfaces an 8-char SHA-256 fingerprint. `audit.audit_log` is correctly RANGE-partitioned with BEFORE UPDATE + BEFORE DELETE triggers raising EXCEPTION, and the GRANT is restricted to `SELECT, INSERT` only — defense-in-depth done right.

The **two material risk areas** are: (1) **inconsistent policy DDL** — half the policies use the helper-function default-deny pattern (`_shared.current_user_id()` → NULL → false) while the other half use the inline `current_setting(...)::uuid` pattern that **throws `invalid_text_representation`** on empty / missing GUC instead of returning empty rows, breaking default-deny posture and creating an information-disclosure side-channel via exception messages; and (2) the **MCP `read_url` SSRF guard** has a known DNS-rebinding hole (explicitly deferred to Wave 1+ per comment line 24) AND a connection-time IP enforcement gap (httpx resolves the IP at connect time, after our pre-resolution check — TOCTOU).

---

## Findings by severity

### Critical (block-the-PR)

*None.*

### High

#### H-1 — Inconsistent RLS policy: `::uuid` cast on empty GUC raises exception instead of default-deny
**Files:**
- `backend/migrations/versions/llm_gateway/0002_byok_keys.py:82-87`
- `backend/migrations/versions/llm_gateway/0002_byok_keys.py:91-98`
- `backend/migrations/versions/llm_gateway/0003_llm_usage_log.py:101-105`
- `backend/migrations/versions/billing/0001_credit_transactions_skeleton.py:74-80`

**Threat:** Default-deny posture is broken for these four policies. The pattern `workspace_id = current_setting('app.current_workspace_id', true)::uuid` raises `invalid_text_representation` (Postgres error 22P02) when the GUC is unset or set to `''` (which is exactly what `clear_tenant_context()` does, `backend/src/_shared/db/rls.py:87-89`).

**Exploit scenario:** When 00.2.5 wires the real request path and a code path forgets to bind the GUC (think: background worker, healthcheck endpoint, partial-failure rollback path), the query raises an unhandled DB exception. The exception:
1. Breaks default-deny — surface becomes "exception" not "empty result set", changing failure mode from secure (deny) to operationally noisy (and potentially info-disclosing through error strings echoed in 500 responses).
2. Diverges from the `multitenancy.*` policies (`workspaces`, `cells`, `cell_members`, `role_assignments`, `mcp_connections`) which correctly use `_shared.current_user_id()` / `_shared.current_workspace_id()` helpers that return NULL on missing/empty GUC → policy evaluates FALSE → zero rows (correct default-deny).

**Mitigation:** Replace inline casts with the helper functions, e.g. `byok_keys_workspace_isolation USING (workspace_id = _shared.current_workspace_id())`. Same for `llm_usage_log` and `credit_transactions`. For `byok_keys_role_restriction` add a NULL-coalesce: `COALESCE(current_setting('app.current_role_slug', true), '') IN ('owner','admin','billing')`.

---

#### H-2 — RLS policies cover SELECT only on the multitenancy tables — UPDATE/INSERT/DELETE are unrestricted
**Files:**
- `backend/migrations/versions/multitenancy/0001_workspaces.py:74-87` (`FOR SELECT`)
- `backend/migrations/versions/multitenancy/0002_cells.py:85-97` (`FOR SELECT`)
- `backend/migrations/versions/multitenancy/0003_cell_members.py:73-85` (`FOR SELECT`)
- `backend/migrations/versions/rbac/0004_role_assignments.py:81-86` (`FOR SELECT`)

**Threat:** Each multitenancy + role_assignments policy declares `FOR SELECT` only. With FORCE RLS enabled and only a SELECT policy, Postgres denies UPDATE/INSERT/DELETE entirely (good — fail-closed). BUT the table also has `GRANT SELECT, INSERT, UPDATE, DELETE ... TO oriion_app`, and once Phase 00.2.5 + 00.5 adds insert/update workflows (e.g. cell_member invite acceptance), the FIRST `INSERT INTO multitenancy.cell_members` will raise `new row violates row-level security policy` because no `FOR INSERT … WITH CHECK (…)` policy exists. The app team will likely "fix" this by adding a permissive INSERT policy in a rush, which is when cross-tenant escalation creeps in.

**Exploit scenario:** Under time pressure to ship 00.2.5, a developer adds `CREATE POLICY cell_members_insert ON multitenancy.cell_members FOR INSERT WITH CHECK (true)` and ships. Now any authenticated user who can bind `app.current_user_id` to their own UUID can `INSERT INTO multitenancy.cell_members (cell_id, user_id, role_id)` for ANY cell — full cross-tenant escalation. This is a phase-handoff trap rather than a current vulnerability.

**Mitigation:** Pre-emptively add INSERT/UPDATE/DELETE policies in Phase 00.3 with proper WITH CHECK clauses, even if Wave 0 has no writes. Pattern: `FOR INSERT WITH CHECK (cell_id IN (SELECT id FROM multitenancy.cells c WHERE EXISTS (SELECT 1 FROM multitenancy.cell_members m WHERE m.cell_id = c.id AND m.user_id = _shared.current_user_id() AND m.role_id IN (...admin roles...))))`. Or document the policy-add procedure in the phase HANDOFF with a security review gate.

---

#### H-3 — SSRF guard has TOCTOU + DNS-rebinding window in `read_url`
**File:** `backend/src/mcp/tools/read_url.py:99-113`, `186-209`

**Threat:** The flow is: `_validate_url` → `getaddrinfo(host)` → check each returned IP against private ranges → `httpx.AsyncClient(...).stream("GET", url)` (which does its OWN DNS resolution internally at connect time). Between the two resolutions an attacker controlling the target hostname can flip the A record from a public IP (passes the check) to `127.0.0.1` / `169.254.169.254` (the actual connect). This is classical DNS-rebinding-SSRF.

The header comment on lines 24-26 acknowledges this: *"Wave 1+ hardening: DNS-rebinding mitigation (resolve once + pass IP to httpx)"* — so the team is aware. Calling this High rather than Medium because: (a) instance-metadata exfil (`169.254.169.254` → AWS / `100.64.0.0/10` → GCP / `fd00::/8` → Yandex Cloud equivalent) is a 1-call wallet-drain via stolen IAM creds, (b) `read_url` is one of two Wave-0-shipped MCP tools and will be in agent-facing prompts on day 1 of 00.5, and (c) the redirect-target SSRF guard (lines 243-254) also re-resolves DNS, repeating the TOCTOU.

**Exploit scenario:** Attacker registers `attacker.example`, sets A record TTL=1, points it at a public IP. They get an Oriion agent to call `read_url("http://attacker.example/")`. Between `getaddrinfo` (resolves to public) and httpx connect (TTL expired, re-resolves), the A record flips to `169.254.169.254`. httpx connects to the GCP/Yandex/AWS instance metadata endpoint, returns IAM credentials in the body, body flows through `readability-lxml` → text_content → back to the agent.

**Mitigation:**
1. Resolve the hostname ONCE, pin to the resulting IP, build the httpx request with `Host:` header preserved but `url` rewritten to the IP literal. (See `python-requests` "transport adapter" + custom resolver patterns).
2. Add a connection-time guard via `httpx.AsyncHTTPTransport(local_address=...)` or an asyncio resolver wrapper that re-validates every IP returned during connect.
3. As a stopgap before Wave 1, **disable `read_url` for untrusted-agent contexts** and only allow it from system/orchestrator agents.
4. Additional layer: refuse hostnames matching cloud-metadata aliases (`metadata.google.internal`, `metadata.yandex.cloud`, `instance-data`, IPv6 `fd00::`).

### Medium

#### M-1 — JWT dev default secret has weak randomness signaling
**File:** `backend/src/_shared/config.py:51-54`

**Threat:** `jwt_secret_access_v1: SecretStr = Field(default=SecretStr("changeme-dev-only-please-replace-in-prod-min-32-chars"))`. The string contains "changeme" but Settings does not refuse to start if `app_env="prod"` and the secret matches this literal. CI deploy could ship this default to production.

**Mitigation:** Add a `model_validator` on `Settings` that asserts `app_env != "prod"` OR `jwt_secret_access_v1.get_secret_value() != "changeme-dev-only-please-replace-in-prod-min-32-chars"`. Same check for `byok_master_key_b64 != ""` when `app_env="prod" and kms_backend="local"`.

---

#### M-2 — `read_url` follows redirects unconditionally; trailing-redirect SSRF guard in event hook only validates ONE redirect
**File:** `backend/src/mcp/tools/read_url.py:188-209`, `243-254`

**Threat:** The `_guard_redirect` event hook calls `_validate_url(str(target))` on the `Location:` header — but `httpx.AsyncClient(follow_redirects=True)` will follow up to httpx's default `max_redirects` (20). The hook fires per redirect, so it does iterate; however the hook checks ONLY the literal `location` header — it does not validate the FINAL connect-time IP after the redirect, just the URL string. Combined with H-3 this is exploitable: redirect to a public host whose DNS flips between the hook call and the next connect.

**Mitigation:** Set explicit `max_redirects=3`, set `follow_redirects=False` and walk redirects in a loop where each leg gets the H-3 mitigation (resolve once + IP-pin).

---

#### M-3 — No `.env.example` file ships with the PR
**File:** *(missing)* `backend/.env.example`

**Threat:** The audit scope requires checking `.env.example` for plaintext secrets / dev defaults. Glob `backend/.env*` returns no files. Settings has 14 env-vars including `JWT_SECRET_ACCESS_V1`, `BYOK_MASTER_KEY_B64`, `BRAVE_SEARCH_API_KEY`, `YANDEX_SEARCH_API_KEY`. Without an `.env.example`, operators have no checklist of what needs to be set vs left default, and the dev defaults in `config.py` (which would work but are insecure) become the de-facto template. Code search confirms `JWT_SECRET_ACCESS_V1_dev` and `BYOK_MASTER_KEY_B64` aren't documented anywhere except as Field descriptions.

**Mitigation:** Add `backend/.env.example` listing every Settings field with safe placeholders (`<replace-me-openssl-rand-base64-32>` for the 32-byte key, etc.) and a `# REQUIRED IN PROD` marker. Reference it from the project README. Also add a gitleaks rule against the literal default JWT secret string.

---

#### M-4 — `docker-compose.dev.yml` hardcodes credentials inline
**File:** `infra/docker-compose.dev.yml:19-22`, `52-53`, `77-81`

**Threat:** `POSTGRES_PASSWORD: oriion-dev`, `MINIO_ROOT_PASSWORD: oriion-dev-s3`, `MINIO_SECRET_KEY: oriion-dev-s3` — these are intentional dev creds, but they're committed plaintext. A dev who copies this compose to staging/prod inadvertently ships them. There is no `.env`-file substitution pattern (`POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?required}`).

**Mitigation:** Refactor to use `${VAR:?error}` substitution requiring an `.env` file. Add gitleaks allowlist with explanation. Document the prod path uses YC Lockbox-injected env-vars per the README.

---

#### M-5 — Pydantic schemas in `llm_gateway` use `extra="ignore"` on the chat completion request
**File:** `backend/src/llm_gateway/schemas.py:101` (`ChatCompletionRequest`), `153` (`EmbeddingRequest`)

**Threat:** `extra="ignore"` silently drops unknown fields. Defense-in-depth principle says POST bodies for sensitive endpoints should use `extra="forbid"` so a typo'd or smuggled field (e.g. a future `system_prompt_override`, `byok_key_id` injected by client) is caught at the validation boundary, not silently ignored. Mass-assignment risk is low today because the request fields are explicit and SQLAlchemy models are populated by service code (not `**req.dict()`), but the precedent is risky.

**Mitigation:** Change `ChatCompletionRequest` and `EmbeddingRequest` to `extra="forbid"`. BYOK already does it (`BYOKKeyCreateRequest:58`). Keep `extra="ignore"` only for response models where forward-compat matters (`ProviderOut`, `BYOKKeyOut`, `Usage`).

---

#### M-6 — `LocalAESKMS` master key length check accepts only 32 bytes silently — no warning when env-default empty
**File:** `backend/src/llm_gateway/services/kms_provider.py:62-75`, `backend/src/_shared/config.py:92-100`

**Threat:** `byok_master_key_b64: SecretStr = Field(default=SecretStr(""))` — empty default. Code path: `KMS_BACKEND=local` (default) + empty `BYOK_MASTER_KEY_B64` → `LocalAESKMS()` constructor raises `ValueError("LocalAESKMS requires BYOK_MASTER_KEY_B64 ...")`. Fail-loud at first BYOK use is correct, but the failure happens lazily on first BYOK request, not at startup. Service can boot apparently-healthy and then 500 the first BYOK request.

**Mitigation:** Add a startup probe (in `main.py` lifespan / `health_service`) that calls `get_kms_provider().encrypt(b"probe")` once and refuses to bind the port if it fails when `KMS_BACKEND=local`. Or change Settings to a `model_validator(mode='after')` that fails-fast.

---

#### M-7 — `byok_keys_role_restriction` has FOR ALL but no WITH CHECK — INSERTs bypass the check on the new row
**File:** `backend/migrations/versions/llm_gateway/0002_byok_keys.py:91-98`

**Threat:** `CREATE POLICY byok_keys_role_restriction ... FOR ALL USING (current_setting('app.current_role_slug', true) IN ('owner','admin','billing'))` — `FOR ALL` requires both `USING` and `WITH CHECK`. Postgres treats a missing WITH CHECK on `FOR ALL` as "use the USING clause", which **does** work for INSERTs, but the more common pitfall is that USING is evaluated against the OLD row for UPDATE/DELETE (correct) and against the NEW row for INSERT (correct via fallback), yet many engineers patching this assume `WITH CHECK` is required. The current behavior happens to be correct; flagging it because of code-clarity and the fact that PostgreSQL docs explicitly recommend always specifying both. Combined with H-1 (`::uuid` cast on possibly-empty `app.current_role_slug`) — note: H-1 only flagged the workspace_id cast; the role_slug here uses `current_setting(..., true)` without cast, so it returns NULL or text safely. Not a runtime defect, just a clarity issue.

**Mitigation:** Add explicit `WITH CHECK (current_setting('app.current_role_slug', true) IN ('owner','admin','billing'))` to the policy.

---

#### M-8 — `set_tenant_context` does not verify session is inside a transaction; `SET LOCAL` outside a TX is a silent no-op
**File:** `backend/src/_shared/db/rls.py:36-78`

**Threat:** Postgres `SET LOCAL` requires being inside a transaction; outside, it raises a WARNING (not an ERROR) and effectively becomes `SET SESSION` for the connection. SQLAlchemy AsyncSession in autocommit/autobegin mode may execute statements outside an explicit transaction depending on configuration. If a caller forgets to `async with session.begin()`, `set_tenant_context` silently corrupts the connection-pool semantics — leaking the GUC to the NEXT request that picks up the pooled connection, until that request's own `SET LOCAL` overrides it. This is a connection-pool tenant-leak vector.

**Mitigation:** Add an assertion at the top of `set_tenant_context`: `assert session.in_transaction(), "set_tenant_context requires an active transaction"`. Better: have it call `await session.begin()` itself if `not in_transaction()`. Add an integration test that asserts GUCs do not leak across pooled connections.

---

#### M-9 — `audit.audit_log` GRANT is correct on parent + seed partitions but new partitions need GRANT at creation time
**File:** `backend/migrations/versions/audit/0001_audit_log_partitioned.py:158-166`

**Threat:** The comment correctly notes (lines 158-163) that Postgres doesn't propagate parent grants to existing partitions, and the migration explicitly grants on each. But the maintenance job that creates new monthly partitions (deferred to Wave 1+) MUST also grant `SELECT, INSERT` at creation. If the maintenance job is forgotten or incorrectly written, INSERTs against the new month's partition will fail with permission-denied — turning audit-log writes into hard 500s. The phase has not yet defined where this maintenance job lives.

**Mitigation:** Ship the maintenance-job SQL or a partman config as part of the audit migration. At minimum, add a CI check that asserts every audit_log partition has the correct GRANT. Document in phase HANDOFF that the maintenance job is a P-AUDIT-2 dependency.

---

### Low / informational

#### L-1 — `_shared.current_user_id()` is plpgsql STABLE but does string-cast inside an exception handler — minor planning cost
**File:** `backend/migrations/versions/_shared/0002_current_user_id_helper.py:36-105`

Informational: the EXCEPTION-handler form prevents inlining by the planner, which on hot paths costs a few microseconds per RLS check. Not a security issue. Document that the helper is intentionally non-inlined for the missing-GUC NULL contract.

---

#### L-2 — `web_search` exposes `BRAVE_SEARCH_API_KEY` / `YANDEX_SEARCH_API_KEY` via constructor; not via SecretStr.get_secret_value()
**File:** `backend/src/mcp/tools/web_search.py:88-94`

The tool reads env directly with `os.environ.get(...)` rather than through the `Settings` SecretStr type. This means the key is held as plain `str` on the instance. Low-severity because the keys never appear in logs (no `logger.info(..., key=...)` paths) — verified. Mitigation: read via `get_settings().brave_search_api_key.get_secret_value()` for consistency.

---

#### L-3 — `read_url` does not enforce `Content-Type` allow-list — binary/JSON-disguised payloads pass readability-lxml unchanged
**File:** `backend/src/mcp/tools/read_url.py:188-225`

Informational: the comment on line 26-28 explicitly defers content-type allow-list to Wave 1+. Adversarial worker-DoS via crafted payload (e.g. XML billion-laughs against lxml) is possible but bounded by the 5MB cap.

---

#### L-4 — `BYOKProxyProvider` holds plaintext key in instance attribute `self._key`
**File:** `backend/src/llm_gateway/providers/byok_proxy.py:70`

Informational: the docstring (lines 56-58) says the instance should be dropped per-request, but nothing enforces it. A future bug that caches the provider in a registry would persist plaintext in memory across requests. Mitigation: add a `__del__` that overwrites `self._key`, or store as `bytearray` so it can be zeroized; better, refactor to pass the key to each method instead of holding it.

---

#### L-5 — `_extract_with_readability` swallows all `Exception` types and lifts as `ReadURLError`
**File:** `backend/src/mcp/tools/read_url.py:222-225`

Informational: broad `except Exception` makes debugging lxml crashes painful and could mask injection-driven crashes in lxml (CVE-prone library historically). Narrow to `(LookupError, lxml.etree.XMLSyntaxError, etree.ParserError, ValueError)` or similar.

---

#### L-6 — `LocalAESKMS` accepts an explicit `master_key` constructor arg with no `repr` shielding
**File:** `backend/src/llm_gateway/services/kms_provider.py:62`

Informational: a `repr(LocalAESKMS(b"...32bytes..."))` doesn't dump the key (the key lives inside `self._aesgcm`, not on `self`), so this is safe by construction. Verified by inspection. Could still benefit from `__repr__` override that prints `<LocalAESKMS master_key=***>` for defensive clarity.

---

#### L-7 — `_hostname_resolves_to_private` returns `False` on DNS failure rather than fail-closed
**File:** `backend/src/mcp/tools/read_url.py:99-105`

The comment justifies this as "let the httpx call surface the real error" — defensible but a fail-closed posture (`return True` → ReadURLError on DNS-fail) is more conservative and stops a class of DNS-poisoning races.

---

## RLS bypass tests recommended for 00.2.5 integration

- **T1** — Open a connection, do not call `set_tenant_context`, run `SELECT * FROM multitenancy.workspaces` → assert zero rows (default-deny). Repeat for `cells`, `cell_members`, `byok_keys`, `llm_usage_log`, `credit_transactions`, `mcp_connections`.
- **T2** — Same as T1 but with `app.current_workspace_id = ''` (empty string). For `byok_keys` / `llm_usage_log` / `credit_transactions` this currently **raises** `invalid_text_representation` — assert this behavior and treat the raise itself as a fail-deny signal you want to convert into "0 rows" (motivates H-1 fix).
- **T3** — Bind `current_user_id` to userA, attempt `INSERT INTO multitenancy.cell_members (cell_id=<userB's cell>, user_id=<userA>, role_id=member)` — assert failure once H-2 INSERT policies land.
- **T4** — Pool-leak test: open 5 connections, on conn-1 set GUCs, commit; pick up conn-1 from pool for a second request that DOES NOT call `set_tenant_context`; assert the previous GUCs do NOT bleed (motivates M-8 fix).
- **T5** — Audit append-only: `INSERT` an audit row, then attempt `UPDATE audit.audit_log SET action='tampered' WHERE id=...` → assert raises `audit.audit_log is append-only`. Same for DELETE.
- **T6** — RLS-bypass via app role attempting `SET ROLE postgres` or `SET LOCAL row_security = off` — assert oriion_app lacks the privilege.
- **T7** — Cross-tenant `byok_keys` read: bind workspace_id=A, attempt SELECT id from byok_keys where workspace_id=B → 0 rows.
- **T8** — Role restriction: bind `app.current_role_slug='member'`, attempt SELECT from byok_keys → 0 rows (only owner/admin/billing should see).
- **T9** — `provision_cell_schema` SECURITY DEFINER privilege check: assert oriion_app cannot directly `CREATE SCHEMA` but CAN call the function and gets the expected schema name back. Also assert the function rejects NULL `cell_uuid`.
- **T10** — SSRF: integration test that `read_url("http://attacker.test/")` returns ReadURLError when the test's DNS resolver returns `127.0.0.1`, and assert it ALSO catches a redirect chain ending in a private IP.
- **T11** — KMS round-trip + tamper: encrypt → flip one byte of ciphertext → assert `decrypt` raises `KMSError("AES-GCM authentication failed ...")`.
- **T12** — Audit log GRANTs: as `oriion_app`, attempt `UPDATE audit.audit_log_2026_05 SET ts = now()` → assert permission-denied at GRANT layer (defense-in-depth, in addition to trigger).
- **T13** — JWT dev-default refusal: start app with `APP_ENV=prod` and unchanged `JWT_SECRET_ACCESS_V1` → assert startup fails (motivates M-1 fix).

---

## Summary

The PR's threat model is **architecturally sound**: 3-GUC RLS + FORCE-RLS on every multi-tenant table + AES-256-GCM BYOK custody + partitioned append-only audit log + scheme-allowlist + SSRF guard + rate-limited tools. The cryptography is correct (12-byte nonces from `secrets.token_bytes`, GCM tag verification, no key reuse risk because per-row nonces are randomly generated and a master key collision needs `2^96` operations). The append-only audit-log triggers are correctly placed (BEFORE UPDATE + BEFORE DELETE on the parent, inheriting to all partitions). GRANT SELECT,INSERT only on audit log is correct defense-in-depth.

The three High findings are all **policy-correctness defects that have not yet been exposed** because Wave 0 ships service-layer + 501 routers — the GUC bind happens only in `set_tenant_context` callers, and no production handler invokes them yet. The findings will become exploitable the moment Phase 00.2.5 wires real handlers, so they should be fixed inside this PR or as the first commit of 00.2.5. H-1 (inline `::uuid` cast → exception vs deny) and H-2 (SELECT-only policies → policy-add trap in 00.2.5) are both 30-minute DDL fixes. H-3 (SSRF DNS-rebind / TOCTOU) is a deeper rework that can land in Wave 1 IF `read_url` is gated to system agents in Wave 0.

Medium findings are operational-readiness gaps: missing `.env.example`, no startup-time KMS probe, no fail-fast on dev-default JWT secret in prod, `extra="ignore"` on chat-completion request. None of them is a runtime vulnerability in Wave 0 but each becomes one as the system grows.

**Recommended PR action:** FLAG. Merge after H-1 is fixed in this PR (4 inline policy DDL edits + a regression test asserting empty-GUC → empty result set). Track H-2 and H-3 as 00.2.5 and Wave-1 blockers respectively. Address Medium findings inside this PR if scope permits, otherwise file them as P-AUDIT-3 / P-AUDIT-4 issues with the 00.5 milestone.
