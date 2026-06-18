# Runbook — Staging bootstrap + 10× demo evidence (Phase 00.6 PR-B)

Founder-executed steps between AI commits **C6** and **C7**. Provisions the
real Yandex Cloud staging stack, materializes secrets, deploys the backend,
seeds the demo user, and runs the 10× «Market & content brief» demo to collect
the Wave-0 anchor evidence (gate `wave-0-to-1.md` D5).

> Prereqs validated in pre-flight: Docker, Terraform v1.15.4, `yc` CLI (folder
> `b1g74vf7snhebom5avhu`), `gh` CLI (account `mrflxxxme`), Russian Trusted Root
> CA installed. `backend/.env` present with live DeepSeek/GigaChat/JWT/BYOK keys.

---

## Step 1 — Provision infra (Terraform)

Full detail in [`infra/terraform/README.md`](../../infra/terraform/README.md).

```powershell
cd infra/terraform
Copy-Item terraform.tfvars.example terraform.tfvars   # then fill secrets
# one-time state bucket bootstrap (see README), then:
terraform init -backend-config="access_key=$env:AWS_ACCESS_KEY_ID" -backend-config="secret_key=$env:AWS_SECRET_ACCESS_KEY"
terraform plan
terraform apply
```

Capture outputs:

```powershell
terraform output vm_public_ip          # → STAGING_VM_HOST
terraform output -raw lockbox_secret_id
terraform output staging_fqdn          # → staging.oriion.dev
```

> ⚠️ `apply` creates billable resources (VM + Managed PG + Redis). Run
> `terraform destroy` once evidence is captured if staging isn't needed 24/7.

## Step 2 — DNS A-record

`oriion.dev` is registered off-Yandex (Terraform `manage_dns=false`), so create
the record at your registrar:

```
staging.oriion.dev.  A  300  <vm_public_ip>
```

Verify before deploying (Caddy ACME HTTP-01 needs it resolving):

```powershell
nslookup staging.oriion.dev
```

## Step 3 — VM bootstrap + infra (one-time)

**AC-W1-9:** the backend + worker read their secrets DIRECTLY from YC Lockbox at
startup — the deploy no longer materializes the *secrets* into `/opt/oriion/.env`.
`.env` now holds ONLY the Lockbox pointer + deploy-time, non-Lockbox vars. The
VM's instance service account must have `lockbox.payloadViewer` on the secret.

```bash
ssh deploy@<vm_public_ip>
# on the VM:
cd /opt/oriion
git clone https://github.com/mrflxxxme/oriion.git .    # or rsync infra/ + scripts/
cat > .env <<'EOF'
# AC-W1-9: app secrets come from Lockbox at runtime — DO NOT put them here.
LOCKBOX_SECRET_ID=<lockbox_secret_id>
YC_CR_REGISTRY=cr.yandex/<YC_CR_FOLDER>
CADDY_SITE_ADDR=staging.oriion.dev
CADDY_ACME_EMAIL=deploy@oriion.dev
# CADDY_GLOBAL_OPTS intentionally unset → auto_https ON (ACME)
WEB_SEARCH_MOCK_MODE=false
# Grafana admin password is consumed by the grafana service (NOT the backend);
# keep it here until a later pass moves it to Lockbox too:
LOCKBOX_GRAFANA_ADMIN_PASSWORD=<grafana-admin-password>
EOF
chmod 600 .env
```

The Lockbox payload (provisioned by `lockbox.tf`) MUST contain every backend
secret: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_ACCESS_V1`, `BYOK_MASTER_KEY_B64`,
`DEEPSEEK_API_KEY`, `YANDEX_IAM_TOKEN`/`YANDEX_CATALOG_ID`, `GIGACHAT_AUTH_KEY`,
`BRAVE_SEARCH_API_KEY`/`YANDEX_SEARCH_API_KEY`. A missing/dev-default secret fails
the deploy fast (`Settings._guard_no_dev_secrets`) instead of booting insecure.

### Secret rotation (no redeploy)

1. Add a new Lockbox secret version: `yc lockbox secret add-version --id <id> ...`.
2. Pick it up WITHOUT a new deploy/image:
   ```bash
   # web tier: gunicorn graceful reload — new workers re-read Lockbox in place.
   docker compose -f infra/docker-compose.staging.yml kill -s HUP backend
   # worker: recreate to re-read (no rebuild).
   docker compose -f infra/docker-compose.staging.yml up -d --force-recreate worker
   ```
   A single-process backend (uvicorn, no gunicorn) refreshes in-process via the
   `SIGHUP` handler in `backend/src/_shared/secret_refresh.py` — same
   `apply_secret_state` rebuild path as startup, so they never drift.

## Step 4 — GitHub Actions secrets + vars

```powershell
gh secret set YC_SA_JSON        --body (Get-Content ~/.yc/sa-key.json -Raw)
gh secret set STAGING_SSH_KEY   --body (Get-Content ~/.ssh/oriion-deploy -Raw)
gh secret set STAGING_VM_HOST   --body "<vm_public_ip>"
gh secret set GRAFANA_API_KEY   --body "<grafana-api-key>"

gh variable set YC_CR_FOLDER    --body "<container-registry-id>"
gh variable set STAGING_DOMAIN  --body "staging.oriion.dev"
gh variable set GRAFANA_URL     --body "https://staging.oriion.dev/grafana"
```

## Step 5 — First deploy

Trigger the deploy workflow manually (before any new push to `main`):

```powershell
gh workflow run deploy-staging.yml
gh run watch
```

It builds + pushes the backend image, SSHes to the VM, `docker compose up -d`,
waits for health, runs `/healthz` + `/metrics` smoke, and annotates Grafana.

Verify by hand:

```powershell
curl -fsSL https://staging.oriion.dev/healthz     # → 200 {"status":"ok",...}
curl -fsSL https://staging.oriion.dev/metrics     # → Prometheus exposition (9 metrics)
# Grafana: https://staging.oriion.dev/grafana  (admin / Lockbox password)
```

## Step 6 — Seed the demo user (fresh PG is empty)

Alembic auto-runs schemas on backend start, but there are no users/cells yet.
Register + login against staging, then capture the JWT + cell_id:

```powershell
$base = "https://staging.oriion.dev/api/v1"

# Register (consent_pdn mandatory). Response carries {user_id, workspace_id, cell_id}.
$reg = curl -fsSL -X POST "$base/auth/register" `
  -H "Content-Type: application/json" `
  -d '{"email":"demo@oriion.dev","password":"<strong-pw>","display_name":"Demo","consent_pdn":true}' | ConvertFrom-Json
$env:DEMO_CELL_ID = $reg.cell_id

# If the email-verification gate is on, verify via the token in the backend log
# (ConsoleEmailSender) or disable the gate for staging (EMAIL_VERIFICATION_REQUIRED=false).

# Login → TokenPair.
$tok = curl -fsSL -X POST "$base/auth/login" `
  -H "Content-Type: application/json" `
  -d '{"email":"demo@oriion.dev","password":"<strong-pw>"}' | ConvertFrom-Json
$env:DEMO_JWT = $tok.access_token
```

## Step 7 — Run the 10× demo

```powershell
cd backend
python -m scripts.demo_market_brief `
  --api-base-url https://staging.oriion.dev/api/v1 `
  --jwt $env:DEMO_JWT `
  --cell-id $env:DEMO_CELL_ID `
  --runs 10 `
  --output ../.planning/gates/evidence/wave-0-to-1/
# add --tolerate-failures 1 to honour the gate D5 «≥9/10» latitude (α decision-7)
```

Produces `summary.json` + `run_001.json … run_010.json`. Check:

- `ac8_cohort_p95_seconds` ≤ 120
- `ac9_per_run_all_pass: true`, `ac10_per_run_all_pass: true`
- `runs_passed` ≥ 9

## Step 8 — Screen-recording

Record ONE run end-to-end (OBS Studio / Loom). API-based evidence is sufficient
per Phase 00.6 spec § «Scope amendment 2026-05-23» (UI demo → Phase 01.1 retro):
show the terminal running the CLI + the Grafana `tasks-pipeline` + `llm-usage`
dashboards updating. Save the link/file into
`.planning/gates/evidence/wave-0-to-1/screen-recording.txt` (or `.mp4`).

## Step 9 — Hand evidence back

Confirm `.planning/gates/evidence/wave-0-to-1/` contains:

- [ ] `summary.json`
- [ ] `run_001.json` … `run_010.json`
- [ ] `screen-recording.{mp4,txt}`

Then the agent resumes at **C7** (commit evidence) → **C9** (5-agent audit +
Wave-0 anchor flip).

---

## Rollback (if a deploy goes bad)

```bash
scripts/deploy/rollback.sh --to-sha <previous-good-sha> --host <vm_public_ip>
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Caddy stuck issuing cert | DNS not propagated / port 80 blocked | confirm `nslookup`; SG allows 80/443 |
| 502 from `/api/*` | backend unhealthy | `ssh … 'docker compose ps'`; check logs |
| demo run exits 2 | transport/auth (JWT expired, cell_id wrong) | re-login (Step 6); confirm cell_id |
| demo AC9 fails | LLM returned short brief / wrong shape | inspect `run_NNN.json` artifacts; retry |
| GigaChat 495/SSL | RU CA not trusted on VM | cloud-init installs it; re-run `update-ca-certificates` |
