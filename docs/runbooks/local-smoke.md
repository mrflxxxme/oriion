# Stage A — Local Smoke Runbook (Phase 00.6 Commit 13)

> Step-by-step founder validation checklist for Phase 00.6 Stage A. Run
> after PR-A merges to `main`. Expected wall-clock: ~15-20 minutes
> (most of it Docker image pulls on first run).

## Pre-flight checklist (one-time)

- [ ] **Docker Desktop** running (≥6 GiB RAM allocated). Verify:
      `docker info --format "RAM: {{div .MemTotal 1073741824}} GiB"`
- [ ] **Russian Trusted Root CA installed** для GigaChat TLS:
      ```powershell
      $dl = "$env:TEMP\ru-ca"
      New-Item -ItemType Directory -Path $dl -Force | Out-Null
      Invoke-WebRequest "https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer" -OutFile "$dl\root.cer"
      Invoke-WebRequest "https://gu-st.ru/content/Other/doc/russian_trusted_sub_ca.cer" -OutFile "$dl\sub.cer"
      # Open elevated PowerShell:
      certutil -addstore -f "Root" "$dl\root.cer"
      certutil -addstore -f "CA"   "$dl\sub.cer"
      # Append to Python certifi bundle (backend container path):
      python -c "import certifi; open(certifi.where(),'ab').write(open(r'$dl\root.cer','rb').read()+open(r'$dl\sub.cer','rb').read())"
      ```
      Альтернатива (dev-only): add `GIGACHAT_VERIFY_SSL=false` к `backend/.env`
- [ ] **YC IAM token freshness** (~12h TTL):
      ```powershell
      $tok = (yc iam create-token --impersonate-service-account-id ajen5nokvbqalrt97tbd).Trim()
      (Get-Content backend\.env) -replace '^YANDEX_IAM_TOKEN=.*', "YANDEX_IAM_TOKEN=$tok" | Set-Content backend\.env -Encoding utf8
      ```
- [ ] **backend/.env** present с all required keys (DEEPSEEK_API_KEY,
      YANDEX_IAM_TOKEN, YANDEX_CATALOG_ID, GIGACHAT_AUTH_KEY,
      JWT_SECRET_ACCESS_V1, BYOK_MASTER_KEY_B64). Validated via
      `python -c "import sys; sys.path.insert(0,'backend/src'); from src._shared.config import Settings; s=Settings(); print('OK')"`

## Step 1 — Bring up the 9-service stack (≤180s healthy)

```powershell
docker compose `
    -f infra/docker-compose.staging.yml `
    -f infra/docker-compose.staging-local.override.yml `
    --env-file backend/.env `
    up -d
# Wait ~30-60s on first run for image pulls (otel/prom/grafana/loki/tempo).
docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml ps
```

**PASS criteria:** All 11 services (backend, postgres, redis, caddy, otel-collector, prometheus, grafana, loki, tempo, alertmanager + builtin Caddy services) show `(healthy)` или `running` в status column.

If backend stays `unhealthy`: `docker compose ... logs backend --tail 50` — verify it could read backend/.env (no `RuntimeError: DATABASE_URL` etc).

## Step 2 — Basic endpoints (≤30s)

```powershell
# Backend liveness
curl -fsS http://localhost:8000/healthz
# Expected: {"status":"ok","version":"0.1.0"}

# Prometheus exposition (9 Phase 00.6 metrics)
curl -fsS http://localhost:8000/metrics | Select-String "llm_request_total|task_duration_seconds|task_queue_depth" | Select-Object -First 5
# Expected: HELP/TYPE lines for each metric

# Caddy passthrough
curl -fsS http://localhost:8080/healthz
# Expected: same response, routed through Caddy → backend
```

## Step 3 — Grafana login + 3 dashboards render

1. Open http://localhost:3000 в browser
2. Login as `admin` / `admin-dev-only-replace` (per docker-compose default; rotate before staging deploy)
3. Click **Dashboards** в sidebar → **Oriion** folder
4. Open each dashboard, verify rendering:
   - **System Health — Phase 00.6**: «Backend availability» stat shows 1.0 (green)
   - **LLM Usage & Cost — Phase 00.6**: «LLM requests / 1m» = 0 (no traffic yet); panels render без «No data» complaint
   - **Tasks Pipeline — Phase 00.6**: «Task queue depth» = 0; AC8 panel thresholds 60s/120s visible
5. Verify Tempo datasource: **Explore** → select **Tempo** → query «Service Map» — should show oriion-backend node

## Step 4 — Seed test user (≤30s)

```powershell
# Register a test user — productivity-core team auto-spawns per AC1.
$body = '{"email":"founder@oriion.dev","password":"DemoPass123!","display_name":"Founder","locale":"ru","consent_pdn":true}'
$r = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/register -Method POST -Body $body -ContentType "application/json"
# Save response — body contains user_id + workspace_id + cell_id
$r | ConvertTo-Json | Tee-Object founder-register.json
$cellId = $r.cell_id

# Login to get an access JWT
$loginBody = '{"email":"founder@oriion.dev","password":"DemoPass123!"}'
$login = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/login -Method POST -Body $loginBody -ContentType "application/json"
$jwt = $login.access_token
```

## Step 5 — 1× REAL-LLM demo run

```powershell
cd backend
uv run python -m scripts.demo_market_brief `
    --api-base-url http://localhost:8000/api/v1 `
    --jwt $jwt `
    --cell-id $cellId `
    --runs 1 `
    --output ../.tmp/demo-smoke/
cd ..
Get-Content .tmp/demo-smoke/summary.json
```

**PASS criteria:**
* `summary.json`: `ac9_passed=true` (brief ≥1500 words + matrix ≥5×4 + content-plan exactly 10 posts)
* Single-run latency observed (для p95 нужно ≥10 runs — Stage B job)
* No transport errors (`runs[0].errors` is empty)

## Step 6 — AC4 alert test

```powershell
# Verify health alert fires when backend goes down
docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml stop backend
Start-Sleep -Seconds 150  # SLO BackendHealthzDown fires after 2m
curl -fsS http://localhost:9093/api/v2/alerts | python -c "import sys, json; alerts=json.load(sys.stdin); print('Active alerts:', [a['labels']['alertname'] for a in alerts if a.get('status',{}).get('state')=='active'])"
# Expected: ['BackendHealthzDown']
# Bring backend back:
docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml start backend
```

## Step 7 — Loki receives logs (≤30s)

1. Grafana → **Explore** → select **Loki** datasource
2. LogQL: `{container=~".*backend.*"} | json | level != "debug"`
3. Time range: «Last 5 minutes»
4. **PASS criteria:** Recent backend log lines visible, JSON-structured fields (`event`, `level`, `timestamp`, optionally `trace_id` if there was a request span)

## Step 8 — Tempo trace visible

1. Trigger one request: `curl http://localhost:8000/healthz`
2. Grafana → **Explore** → select **Tempo** → query «TraceQL» → `{service.name="oriion-backend"}`
3. Recent traces should appear с spans named `GET /healthz`
4. Click a trace — verify span graph renders + parent/child relationships present
5. **PASS criteria:** Trace visible с at least one span; if AC4 alert run completed, traces для task.created → orchestrator → llm_gateway → deepseek (real chain) also visible

## Step 9 — Teardown

```powershell
docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml down
# Keep volumes for next run, OR purge data:
docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml down -v
```

## Sign-off

When все steps 1-8 pass, sign off в the PR-A pull-request comment:

```
Stage A local validation: ✅ PASS
* docker compose up → 11 services healthy in <Xs>
* /healthz → 200; /metrics → 9 metrics exposed
* Grafana 3 dashboards render
* 1× demo run → ac9_passed=true
* AC4 alert fires когда backend kill
* Loki + Tempo correlation visible
* Signed: <founder name>, <date>
```

After sign-off, PR-A merges; Stage B (PR-B Terraform + 10× demo + Wave-0
anchor flip) kicks off.

## Troubleshooting

| Issue | Likely cause | Fix |
|---|---|---|
| backend container unhealthy | `.env` not mounted / missing required env | Verify `--env-file backend/.env` flag в compose-up command |
| Grafana «No data» everywhere | otel-collector down OR Prometheus can't scrape backend | Check `docker compose logs otel-collector prometheus` |
| GigaChat OAuth 502/SSL error | RU CA not installed | См. Pre-flight Step 2 |
| Demo run hangs >120s | LLM provider hung / IAM token expired | Refresh YC IAM token; check `docker compose logs backend | grep llm_gateway` |
| `task_queue_depth` panel stays 0 | metrics не instrumented at callsites yet | Wave-1 AC-W1-2 (per-callsite instrumentation deferred) — expected at Phase 00.6 |
