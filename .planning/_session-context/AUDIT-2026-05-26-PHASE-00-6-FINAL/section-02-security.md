## Section 02 — Security

**Auditor:** Security Engineer (5-agent Phase 00.6 retrospective)
**Scope:** Phase 00.6 PR-B (branch `claude/gallant-lamport-f48eca`, commits `165b6ea`→`37bb934`) + PR-A observability residency carry-over.
**Method:** Direct file read of Terraform (`infra/terraform/*.tf`), GitHub Actions (`deploy-staging.yml`), Caddy (`Caddyfile.staging`), orchestrator-dispatch (`backend/src/runtime/dispatch.py` + `backend/src/tasks/routers/tasks.py` + `tenant_context.py`), observability configs, ADR-014, `.gitignore`. `git ls-files` + `git check-ignore -v` used to prove no secret/state/binary is tracked. No real secret values were read or exfiltrated.

---

### Verdict: **APPROVE WITH CAVEATS**

No HIGH findings. No committed secret, no committed `*.tfstate`/`*.tfvars`/`.terraform` binary, no cross-tenant access path, no secret logged or echoed to CI output. The one notable risk (SSH `0.0.0.0/0`) is already explicitly flagged in-code and pinned to Wave-1 hardening, consistent with a staging-only Wave-0 anchor. Caveats are all MEDIUM/LOW deferrals already tracked under AC-W1-* and do not block the Wave-0 anchor flip.

---

### Strengths

- **Secrets hygiene is correct and verified.** `.gitignore:69-79` ignores `**/.terraform/*`, `*.tfstate*`, `*.tfvars` (with `!*.tfvars.example` allow), `override.tf*`, `crash.log`. `.gitignore:2-7` ignores `.env`, `.env.*` (with `!.env.example`), `*.key`, `*.pem`, `secrets/`. `git ls-files infra/terraform/` confirms only the 15 `.tf` source files + the *committed* `.terraform.lock.hcl` (correct — reproducible provider pins) are tracked; the ~50 MB `terraform-provider-yandex_v0.206.0.exe` and `terraform.tfvars` and `backend/.env` are all `check-ignore`-confirmed ignored and untracked.
- **Lockbox sourced exclusively from sensitive vars — zero hardcoded secrets.** `lockbox.tf:29-62` every secret entry (`DEEPSEEK_API_KEY`, `YANDEX_GPT_API_KEY`, `GIGACHAT_AUTH_KEY`, `JWT_SECRET`, `BYOK_MASTER_KEY_B64`, `GRAFANA_ADMIN_PASSWORD`) is `var.lockbox_*`; `variables.tf:154-198` marks each `sensitive = true` with empty default. DB/Redis DSNs are computed from `random_password` (`managed_pg.tf:3-6`, `managed_redis.tf:3-6`), never literal. `terraform.tfvars.example` contains placeholders only (`sk-...`, `min-32-char-...`), no real keys.
- **FZ-152 RU-residency enforced at plan time.** `variables.tf:27-31` validation block rejects any `yc_zone` not matching `^ru-central1-`. PG and Redis hosts pin `zone = var.yc_zone` (`managed_pg.tf:28`, `managed_redis.tf:27`).
- **No public IP on managed data stores.** `managed_pg.tf:30` `assign_public_ip = false`; Redis has no public-IP assignment and `tls_enabled = true` (`managed_redis.tf:12`) producing a `rediss://` DSN. Both reachable only intra-SG.
- **Tenant isolation is real and defense-in-depth.** The `/run` endpoint (`tasks.py:62-102`) and `get_task_service` (`tasks.py:22-25`) both depend on `get_tenant_db_session`, which sets the 3-GUC RLS context (`tenant_context.py:106-112`) before any query. A cross-tenant `task_id` is filtered by RLS → `get_task` raises `TaskNotFound` → 404 (no enumeration leak). Child `Task` rows written by `dispatch.py:175-190` go through the same scoped session, so RLS `WITH CHECK` blocks cross-cell inserts. Membership lookup uses a `SECURITY DEFINER` function (`tenant_context.py:68-71`) — the sole owner-context path, per ADR-014.
- **No secret logging in dispatch.** Grep of `backend/src/runtime/` shows only numeric token-*count* usage (`input_tokens`/`output_tokens`), never auth tokens or API keys. LLM provider keys are constructed inside `LLMGatewayModel`/`LLMRouter` from env (Lockbox-injected), in-memory only; `dispatch.py` never touches key material.
- **CI does not echo secrets.** `deploy-staging.yml:52` pipes `secrets.YC_SA_JSON` straight to `docker login --password-stdin` (never printed); the SSH key (`STAGING_SSH_KEY`) and `GRAFANA_API_KEY` are passed via `appleboy/ssh-action` `with:` and a `curl -H Authorization` body, not `echo`-ed. All registered GitHub secrets are auto-masked in logs. Actions are version-pinned (`actions/checkout@v4`, `appleboy/ssh-action@v1.0.3`). `permissions: contents: read` is least-privilege.
- **PR-B adds zero Python deps** — `git diff` on `backend/pyproject.toml` shows only ruff `per-file-ignores` additions (RU-content lint suppressions). The ADR-014 pip-audit advisory registry (PYSEC-2025-183 / CVE-2025-69872 / PYSEC-2026-161) remains current; no new attack surface introduced.

---

### Findings

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| F-SEC-01 | MEDIUM | `network.tf:38-43` security-group ingress opens **SSH (port 22) to `0.0.0.0/0`**. Globally exposed SSH is a brute-force / 0-day surface even with key-only auth. | **ACCEPT (deferred).** Already flagged in-code (`network.tf:16-18, 41` "restrict to known IPs in Wave-1") and bound to Wave-1 hardening. Acceptable for a short-lived staging anchor since auth is SSH-key-only (`compute.tf:33`, no password). Recommend pinning to the deploy runner egress range / office IP before any prod or persistent-staging promotion. Non-blocking. |
| F-SEC-02 | MEDIUM | `docker-compose.staging.yml:128` `GF_SECURITY_ADMIN_PASSWORD: ${LOCKBOX_GRAFANA_ADMIN_PASSWORD:-admin-dev-only-replace}` ships a **weak default fallback password**. If the Lockbox/env var is unset on the VM, Grafana boots with a guessable admin password, and `/grafana/*` is internet-reachable via Caddy. | **ACCEPT WITH ACTION.** Not a committed *real* credential (it is a `:-` fallback, overridden by Lockbox in prod per `lockbox.tf:59-62`). The staging-bootstrap runbook materializes the Lockbox value into `/opt/oriion/.env` before `compose up`, so the fallback should never apply. Mitigation: verify the bootstrap step asserts a non-empty `LOCKBOX_GRAFANA_ADMIN_PASSWORD` (fail-closed) rather than silently falling back. Track under the AC-W1 Grafana-hardening pin. Non-blocking. |
| F-SEC-03 | MEDIUM | `Caddyfile.staging:89-94` proxies `/grafana/*` with **Caddy `basic_auth` defense-in-depth layer deferred** — currently only Grafana's own login gates the panel. Comment (`Caddyfile.staging:83-88`) explains the empty-bcrypt-default crash that forced deferral. | **ACCEPT (deferred).** Single-layer auth (Grafana built-in, anonymous disabled via `GF_AUTH_ANONYMOUS_ENABLED=false`, signup off) is acceptable for Wave-0 staging. The `basic_auth` defense-in-depth pin is already documented (AC-W1) and gated on a Lockbox-injected bcrypt env. Resolution coupled with F-SEC-02. Non-blocking. |
| F-SEC-04 | LOW | `object_storage.tf:17-21` Loki-archive service account is granted **`storage.editor` at the folder level**, not bucket-scoped. `storage.editor` on the whole folder is broader than the single archive bucket needs (least-privilege deviation). | **ACCEPT (deferred).** YC `storage.editor` is the standard role for static-key S3 access and the SA is single-purpose (`oriion-staging-storage-sa`). Folder-scope vs bucket-scope on YC is awkward to tighten in Wave-0. Recommend narrowing to bucket-level IAM binding in Wave-1 when the AC-W1-14 archival wiring lands. Bucket itself is correctly non-public (`anonymous_access_flags { read=false, list=false }`). Non-blocking. |
| F-SEC-05 | LOW | `managed_pg.tf:59-67` builds `DATABASE_URL` **without `sslmode=verify-full`** (comment acknowledges it would need the YC root CA on the VM). Traffic is intra-SG private but unverified-TLS to managed PG. `compute.tf:59` already installs the YC Root CA via cloud-init, so the prerequisite is partially in place. | **ACCEPT (deferred).** Intra-SG private network limits exposure; the CA is being installed. Recommend appending `?ssl=verify-full` (asyncpg) / mounting the CA path once the cloud-init CA install is verified, as a Wave-1 hardening step. Non-blocking. |
| F-SEC-06 | LOW | Observability data-residency: `loki.yaml:58` retention `168h` (7d) and `tempo.yaml:29` `block_retention: 168h`, both **filesystem-local on the RU-zoned VM**. ADR-009 RU-residency is satisfied (data never leaves the `ru-central1` VM disk), but the Object Storage archive bucket (`object_storage.tf`) is **provisioned but not yet wired** to Loki — long-term log/audit residency depends on AC-W1-14. | **ACCEPT.** Wave-0 residency is compliant (RU VM, no cross-border egress; FZ-152 audit-ledger stays in РФ). The 90d S3 archival target exists (`object_storage.tf:28-45`, RU bucket, 90d lifecycle) awaiting Wave-1 wiring. Confirm 3-year FZ-152 audit-log retention (ADR-014 §3) is met by the DB `audit.audit_log`, not Loki (Loki is operational logs, correctly short-retention). Non-blocking. |
| F-SEC-07 | LOW | `Caddyfile.staging:118-121` access log is JSON to stdout with **no field redaction** — request paths/headers flow to Loki. If a future endpoint accepts secrets in query strings or a client sends an `Authorization` header that Caddy logs, PII/secret material could land in operational logs (currently no such endpoint exists; auth is header-bearer not query-param). | **ACCEPT (advisory).** No current leak — Wave-0 auth uses `Authorization: Bearer` (not logged by Caddy default access log) and no secret-in-query endpoint exists. Recommend a `log` block field-filter (drop `Authorization`, `Cookie`) as a cheap Wave-1 DLP hardening before prod traffic. Non-blocking. |
| F-SEC-08 | INFORMATIONAL | `deploy-staging.yml:91-98` Grafana annotation step is `continue-on-error: true` and posts with `GRAFANA_API_KEY` over `${{ vars.GRAFANA_URL }}` (a *variable*, not secret). If `GRAFANA_URL` were ever attacker-controlled, the bearer token could be sent to an arbitrary host. | **ACCEPT (informational).** `vars.GRAFANA_URL` is a repo-admin-controlled GitHub variable, not user input — low realistic risk. Note for the threat model: treat deploy-config `vars.*` as a trust boundary; an org member with `vars` write could redirect the token. Non-blocking. |

---

### Cross-tenant attack-path analysis (explicit, HIGH-class check — PASS)

Attempted to construct a cross-tenant task-run exploit against `POST /api/v1/cells/{cell_id}/tasks/{task_id}/run`:
1. `cell_id` in the path is **routing scope only** (`tasks.py:84` `_ = cell_id`); it is *not* trusted for authorization — RLS at the DB layer is authoritative. This is the correct posture (path param cannot be used to escalate).
2. Both `service.get_task(task_id)` and the `db` session are tenant-GUC-scoped via `get_tenant_db_session`. A `task_id` belonging to another cell evaluates RLS FALSE → 0 rows → `TaskNotFound` → 404. No cross-tenant read, no cross-tenant dispatch.
3. Child rows written during dispatch inherit `cell_id = task.cell_id` (`dispatch.py:177`) and are inserted through the scoped session → RLS `WITH CHECK` blocks any mismatch.
**Result:** no cross-tenant access path found. No HIGH finding.

---

### Recommendations (priority order, all Wave-1)
1. Pin SSH ingress to known IPs (F-SEC-01) — highest residual risk before any persistent/prod promotion.
2. Make `LOCKBOX_GRAFANA_ADMIN_PASSWORD` fail-closed in bootstrap + restore Caddy `basic_auth` (F-SEC-02 + F-SEC-03).
3. Narrow Loki-archive SA to bucket-scope IAM (F-SEC-04); enable `sslmode=verify-full` on `DATABASE_URL` (F-SEC-05).
4. Add Caddy access-log field redaction for `Authorization`/`Cookie` (F-SEC-07).
