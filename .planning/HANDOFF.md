# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-23 (Phase 00.6 PR-A — mid-session checkpoint: Commits 1-3 of ~14 done)
- Session: `great-engelbart-8aa6fc` (worktree branch `claude/great-engelbart-8aa6fc`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — anchor flips at Phase 00.6 PR-B staging demo run
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete (PR #25)
- **Architect-PR (pre-00.2)**: ✅ Complete (PR #27)
- **Phase 00.2 (Custom JWT auth)**: ✅ Complete (PR #28)
- **Phase 00.3 + Phase 00.4**: ✅ Complete (PR #30)
- **Phase 00.2.5 (integration)**: ✅ Complete (PR #32)
- **Pre-Phase-05 audit + nav cleanup**: ✅ Complete (PR #33)
- **Phase 00.5a (RLS foundation)**: ✅ Complete (PR #34, merge `0360955`)
- **Phase 00.5 / 00.5b (Pydantic-AI productivity-core + runtime)**: ✅ Complete (PR #35, merge `f250de0`)
- **Phase 00.6 (Deploy + Observability)**: 🔄 **In Progress — PR-A Commits 1-3 of ~14 landed; pause for continuation**

## What just happened (this session, 2026-05-23)

Founder invoked `/anthropic-skills:grill-me` для Phase 00.6 planning. Session shape:

### Pass 1 (2026-05-23) — Grill + Commits 1-3
- 10-question structured grill walked decision tree от scope envelope до Stage B IaC choice
- 13 decisions locked (see «Decisions standing» table below)
- Phase-spec amended к 2-stage execution (PR-A local + PR-B YC deploy)
- 14-commit ledger drafted и pinned в TaskList
- 3 hygiene + spec commits landed:
  * `eb31ff8` Phase 00.6 spec amendment + STATUS.md In Progress flip
  * `dd9fa2d` alembic.ini cp1251 real-fix via env.py UTF-8 patch
  * `588e979` auth_service.register → async-with set_tenant_context (closes F-CR-M2 + F-ARC-M4)
- Session pauses перед heavy observability + IaC + tests work (C4-C14)

## Phase 00.6 PR-A commit ledger (mid-checkpoint)

| # | Hash | Title | Status |
|---|---|---|---|
| C1 | `eb31ff8` | `docs(planning,roadmap)`: Phase 00.6 spec amendment к 2-stage version | ✅ Landed |
| C2 | `dd9fa2d` | `chore(alembic)`: force UTF-8 alembic.ini read via env.py patch | ✅ Landed |
| C3 | `588e979` | `refactor(iam)`: auth_service.register uses async-with set_tenant_context | ✅ Landed |
| C4 | _(TBD)_ | `feat(_shared/observability)`: OpenTelemetry SDK setup + auto-instrumentation | 🔄 Next |
| C5 | _(TBD)_ | `feat(_shared/observability)`: Prometheus custom metrics + /metrics endpoint | ⏳ Pending |
| C6 | _(TBD)_ | `feat(_shared/observability)`: structlog JSON logging refinement for Loki | ⏳ Pending |
| C7 | _(TBD)_ | `feat(infra)`: docker-compose.staging.yml + observability service configs | ⏳ Pending |
| C8 | _(TBD)_ | `feat(infra)`: docker-compose.staging-local.override.yml + Caddyfile HTTP toggle | ⏳ Pending |
| C9 | _(TBD)_ | `feat(infra)`: Grafana provisioning + 3 dashboards | ⏳ Pending |
| C10 | _(TBD)_ | `test(tasks)`: tests/tasks/ unit tests до 85% per-module | ⏳ Pending |
| C11 | _(TBD)_ | `test(runtime)`: tests/runtime/ unit tests до 85% per-module | ⏳ Pending |
| C12 | _(TBD)_ | `ci(backend)`: per-module ≥85% loop для agents/tasks/runtime | ⏳ Pending |
| C13 | _(TBD)_ | `test,docs(observability,runbooks)`: smoke test + local-smoke runbook | ⏳ Pending |
| C14 | _(TBD)_ | `chore(audit,docs)`: 5-agent audit + in-loop fixes + Exit ritual + PR-A open | ⏳ Pending |

**Next session resumes at C4.** TaskCreate ledger 14 tasks pinned (tasks #1-3 completed; #4 in_progress; #5-14 pending).

## Decisions standing (no re-grill — verbatim from 2026-05-23 grill)

| # | Topic | Decision | Status |
|---|---|---|---|
| 1 | **Scope envelope** | B — Spec + Wave-1 hygiene; GLM-5 silent defer без ADR | ✅ Locked |
| 2 | **Execution model** | D-extended — Local-first validation, then VM deploy | ✅ Locked |
| 3 | **Worktree** | Current `claude/great-engelbart-8aa6fc` (PR #33 canonical naming) | ✅ Auto-resolved |
| 4 | **PR strategy** | (ii) 2 PRs — PR-A (local) + PR-B (YC+demo+anchor) | ✅ Locked |
| 5 | **Compose pattern** | A — base `staging.yml` + `staging-local.override.yml` | ✅ Locked |
| 6 | **Local-pass acceptance** | 3 — Smoke + Grafana + 1 REAL-LLM demo + AC4 alert + Loki+Tempo visible | ✅ Locked |
| 7 | **Gate D5 anchor flip** | α — Update D5 verbatim: founder runs script 10× against staging URL | ✅ Locked (Stage B amendment) |
| 8 | **5-agent audit swarm** | IV — Full 5-agent on PR-A; lightweight (Security+Compliance) on PR-B | ✅ Locked |
| 9 | **AC13 ≥85% per-module** | (i) Strict honor — write ~10 unit-test files, relocate tests, strict CI loop | ✅ Locked |
| 10 | **F-CR-M2/F-ARC-M4 GUC** | (A1) — Wrap `auth_service.register` with `async with set_tenant_context()` | ✅ Shipped C3 |
| 11 | **alembic.ini cp1251** | (B1) — Patch `env.py` to read ini with `encoding="utf-8"` | ✅ Shipped C2 |
| 12 | **Stage B IaC** | (1) — Terraform-only; `winget install Hashicorp.Terraform` between Stage A & B | ✅ Locked |
| 13 | **AC tolerance band** | AC8 cohort p95 ≤120s (n=10); AC9+AC10 per-run all-pass; fix `demo_market_brief.py` AC8 semantic в PR-B | ✅ Locked |

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

## Next agent — read first (bootstrap-4)

1. [`README.md`](./README.md)
2. [`STATUS.md`](./STATUS.md)
3. **this HANDOFF.md**
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md)

Then for Phase 00.6 continuation:

5. [`roadmap/wave-0-foundation/phases/00.6-deploy-observability.md`](./roadmap/wave-0-foundation/phases/00.6-deploy-observability.md) — read the new «Scope amendment 2026-05-23» section at the top
6. `git log eb31ff8..HEAD --oneline` для cross-check Phase 00.6 commits landed so far
7. TaskList — 14-task PR-A ledger; resume task #4 (C4 — OpenTelemetry SDK setup)

## Founder action (parallel с next agent C4-C14 work)

Provision live LLM keys для Stage A local validation acceptance (per decision #6):
1. **DeepSeek API key** — https://platform.deepseek.com/api_keys. Save в `backend/.env.local` as `DEEPSEEK_API_KEY=sk-...`
2. **YandexGPT** — Yandex Cloud service account → `iam token` + `folder/catalog ID`. Save:
   ```
   YANDEX_IAM_TOKEN=t1...
   YANDEX_CATALOG_ID=b1g...
   ```
3. **GigaChat OAuth** — https://developers.sber.ru/portal/products/gigachat. Save `GIGACHAT_AUTH_KEY=Basic ...`
4. Optional: install Terraform для Stage B prep — `winget install Hashicorp.Terraform`

## Phase 00.6 PR-A — C4-C14 work plan (for next session)

### C4 — OpenTelemetry SDK setup (estimate ~30 min)
- Add deps to `backend/pyproject.toml`:
  ```
  opentelemetry-api>=1.39,<2.0
  opentelemetry-sdk>=1.39,<2.0
  opentelemetry-exporter-otlp-proto-grpc>=1.39,<2.0
  opentelemetry-instrumentation-fastapi>=0.60b0
  opentelemetry-instrumentation-httpx>=0.60b0
  opentelemetry-instrumentation-asyncpg>=0.60b0
  ```
- Create `backend/src/_shared/observability/__init__.py` (empty package marker)
- Create `backend/src/_shared/observability/otel_setup.py` with `setup_otel(service_name, otlp_endpoint)` per phase-spec signature
- Wire setup_otel() в `src/main.py::lifespan` ПОСЛЕ `configure_structlog()` но ДО router includes  
- `Settings` getter: add `otel_exporter_otlp_endpoint: str` (default `http://otel-collector:4317`) + `otel_service_name: str` (default `oriion-backend`)
- pip-audit может выкинуть новые advisories на bumped opentelemetry — register в ADR-014 table if так

### C5 — Prometheus custom metrics (estimate ~45 min)
- Add `prometheus-client>=0.21,<0.22` to pyproject deps
- Create `backend/src/_shared/observability/metrics.py` per phase-spec signature: Counter `LLM_REQUEST_TOTAL`, `LLM_TOKENS_INPUT`, `LLM_TOKENS_OUTPUT`, `LLM_COST_RUB`; Histogram `LLM_LATENCY`, `TASK_DURATION`; Gauge `LLM_PROVIDER_HEALTH`, `TASK_QUEUE_DEPTH`; Counter `TASK_TOTAL`
- `register_default_metrics()` idempotent (guard against double-registration)
- Mount `/metrics` endpoint в `src/main.py` via `from prometheus_client import make_asgi_app; app.mount("/metrics", make_asgi_app())`
- Integration touchpoints (defer wiring к Wave-1+):
  * `runtime/orchestrator.py::execute_agent_task` — increment TASK_TOTAL + TASK_DURATION на entry/exit
  * `llm_gateway/services/router_service.py::LLMRouter.chat` — increment LLM_REQUEST_TOTAL + LLM_LATENCY + LLM_TOKENS_*
  * `llm_gateway/services/cost_recorder.py` — increment LLM_COST_RUB на каждый рекорд
  * `llm_gateway/circuit_breaker.py` — set LLM_PROVIDER_HEALTH gauge при open/half-open/close
  * Phase 00.6 PR-A может wire ТОЛЬКО `register_default_metrics()` + /metrics endpoint; per-callsite instrumentation = Wave-1 hardening (avoid scope inflation)

### C6 — structlog JSON refinement for Loki (estimate ~20 min)
- `_shared/logging.py::configure_structlog` уже exists; verify JSON output to stdout (Loki tails stdout)
- Add fields: `trace_id` + `span_id` (OTel context propagation) + `cell_id` (where in request scope)
- Logfmt → JSON transition if not already JSON

### C7 — docker-compose.staging.yml + observability service configs (estimate ~90 min)
- Per phase-spec inline skeleton exactly
- 9 services: backend, frontend, caddy, otel-collector, prometheus, grafana, loki, tempo (and Promtail для log shipping в Loki — может skip если Loki tail container stdout direct)
- `infra/observability/`:
  * `otel-collector-config.yaml` — OTLP gRPC receiver → Tempo (traces) + Prometheus (metrics) + Loki (logs)
  * `prometheus.yml` — scrape configs per spec inline
  * `alerting/{slo-availability.yml, latency-p95.yml, llm-budget.yml}` per spec
  * `loki.yaml` — local-only filesystem retention
  * `tempo.yaml` — local-only filesystem retention
- managed PG/Redis via `${LOCKBOX_DATABASE_URL}` / `${LOCKBOX_REDIS_URL}` env-vars

### C8 — staging-local.override.yml + Caddyfile (estimate ~60 min)
- `infra/docker-compose.staging-local.override.yml` adds:
  * `postgres:` service (postgres:16-alpine + volume)
  * `redis:` service (redis:7-alpine)
  * Override `DATABASE_URL=postgresql+asyncpg://oriion:oriion@postgres:5432/oriion`
  * Override `REDIS_URL=redis://redis:6379/0`
  * Override `CADDY_TLS=off` env
- `infra/caddy/Caddyfile.staging` — env-based TLS toggle: `{$STAGING_DOMAIN}:{$CADDY_PORT}` с conditional `tls deploy@oriion.dev` блок (presence-checked via `{$CADDY_TLS:on}`)

### C9 — Grafana provisioning + 3 dashboards (estimate ~90 min, biggest single commit)
- `infra/observability/grafana/provisioning/datasources.yaml` — prometheus + loki + tempo
- `infra/observability/grafana/provisioning/dashboards.yaml` — file-based provider
- `infra/observability/grafana/dashboards/system-health.json` — requests/s, p95 latency, /healthz status
- `infra/observability/grafana/dashboards/llm-usage.json` — LLM_REQUEST_TOTAL by provider, LLM_COST_RUB by cell, LLM_LATENCY p50/p95/p99
- `infra/observability/grafana/dashboards/tasks-pipeline.json` — TASK_DURATION distribution, TASK_QUEUE_DEPTH, TASK_TOTAL by outcome

### C10 — tests/tasks/ unit tests (~6-8 files, estimate ~120 min, ~85% target)
- Create `backend/tests/tasks/__init__.py` + `conftest.py` if needed
- `test_task_service_crud.py` — TaskService.create_task, get_task, list_tasks_for_cell
- `test_task_service_cancel.py` — relocate from tests/agents/test_cancel_cascade.py; covers BFS walker + cascade semantics
- `test_cost_rollup_service.py` — rollup_task_cost atomicity + sum invariants
- `test_models.py` — Task / TaskStep / TaskArtifact ORM mapping
- `test_schemas.py` — Pydantic schemas validation
- `test_exceptions.py` — TasksError subclass hierarchy + code/title mapping
- `test_events.py` — CloudEvent emit shapes

### C11 — tests/runtime/ unit tests (~3-4 files, estimate ~75 min, ~85% target)
- `test_orchestrator.py` — execute_agent_task state machine (queued→running→succeeded/failed); task.failed SSE emit on exception + budget refund
- `test_sse_publisher.py` — InProcessSSEPublisher subscribe + drain-replay semantics
- `test_budget_guard.py` — 50 T-credit cap + budget_exceeded raise
- `test_sse_events.py` — SSE event-type vocabulary serialization

### C12 — ci-backend.yml per-module loop (estimate ~15 min)
- Extend lines 165-178 with:
  ```yaml
  uv run pytest tests/agents   --cov=src/agents   --cov-fail-under=85 -q -m "not integration"
  uv run pytest tests/tasks    --cov=src/tasks    --cov-fail-under=85 -q -m "not integration"
  uv run pytest tests/runtime  --cov=src/runtime  --cov-fail-under=85 -q -m "not integration"
  ```

### C13 — observability unit tests + local-smoke runbook (estimate ~45 min)
- `backend/tests/_shared/observability/__init__.py` + `test_metrics.py` — register_default_metrics idempotent + key metrics present assertion
- `docs/runbooks/local-smoke.md` — step-by-step founder validation checklist matching decision #6 acceptance bar (9 services healthy + /healthz + /metrics + Grafana login + 1× demo run + AC4 alert test + Loki query + Tempo trace)

### C14 — 5-agent audit + Exit ritual + PR-A open (estimate ~90 min)
- Spawn 5 audit agents в parallel via Agent tool с subagent_type:
  * Code Reviewer — observability code surface + hygiene refactor correctness
  * Security Engineer — OTel attribute leakage, Grafana exposure, structlog ПДн redaction
  * Test Results Analyzer — AC13 coverage + test reorganization adequacy
  * Backend Architect — observability placement (`_shared/observability/`), DI wiring
  * Compliance Auditor — ФЗ-152 + tracing data residency, ADR-014 amendments
- Master report к `.planning/_session-context/AUDIT-2026-05-23-PHASE-00-6-PR-A/AUDIT-REPORT.md`
- Apply HIGH findings in-loop; defer MEDIUMs to Wave-1 AC pins
- Exit ritual: JOURNAL.md append, HANDOFF.md rewrite (mark PR-A code-complete), STATUS.md update
- Open PR-A via `gh pr create` with comprehensive description

## Known caveats (carryover)

- **F-ARC-H2 SSEPublisher multi-worker** — Wave 0 deploys with `workers=1` per Phase 00.6 spec; Wave 1 Redis pubsub swap on AC-W1-1
- **Slug-based cross-tenant linkage** — Wave-1 backlog (unchanged)
- **TOCTOU SSRF in `read_url`** — Wave-1 hardening (unchanged)
- **alembic.ini cp1251 on Windows** — ✅ **CLOSED Commit 2** (env.py UTF-8 patch). Remove from Pitfalls list at PR-A finalization
- **F-CR-M2 + F-ARC-M4 (auth_service.register GUC duplication)** — ✅ **CLOSED Commit 3** (async-with refactor)
- **Live LLM provider tests (`@pytest.mark.live`)** — Phase 00.6 Stage A founder local validation per decision #6
- **GigaChat OAuth refresh-after-expiry test (F-P5-4)** — AC-W1-10 Wave-1 pin

## Pitfalls confirmed (final)

- Worktree-prefixed absolute paths in Edit/Write
- `oriion_app` role canary in CI (verified green в Phase 00.5b suite)
- `rbac.system_roles` natural key is `slug` (NOT `code`)
- ADR-024 §3 amendment lands в SAME PR as the cross-context import что needs sanction
- pytest-xdist remains disabled
- `.claude/settings.local.json` gitignored
- Pip-audit `PYSEC-2025-183` ignore preserved; **NEW** for PR-A: opentelemetry bump может pull новые transitive CVEs — register в ADR-014 table if so
- Lifespan + tests: `dependency_overrides`-only path для unit suite; production handlers depend on lifespan-built `app.state`

## Exit ritual completed (this mid-session checkpoint)

- [x] JOURNAL.md entry — _(deferred к C14 final Exit ritual; mid-session checkpoint не требует JOURNAL append per Phase 00.5b precedent — checkpoint в HANDOFF только)_
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md updated (Commit 1 already flipped Phase 00.6 к In Progress)
- [x] Phase 00.6 PR-A ledger pinned + TaskList 14 tasks
- [x] Decisions standing table verbatim из grill
- [ ] PR opened — Не сейчас; C14 в next session opens PR-A
