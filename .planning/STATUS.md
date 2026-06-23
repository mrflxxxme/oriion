# STATUS — текущее состояние проекта

> Rolling-status. Обновляется при phase complete / blocker resolved / новом ADR.

## Wave-progress

| Wave | Status | Anchor target |
|---|---|---|
| Pre-Wave-0 | ✅ Complete | Roadmap reorg per [Session-2026-05-15](./JOURNAL.md) |
| Wave 0 (Foundation) | 🔄 **Closing** (build phases 00.1–00.7 ✅; architecture **live-validated locally**; remaining: **Phase 00.8 design restyling** (NEW per ADR-031) + founder staging 10× anchor run) | Horizontal `productivity-core` team — internal demo «Market & content brief» |
| Wave 1 (Core MVP) | 🔄 **In progress** — 01.1-retro ✅ COMPLETE (#58–66); **01.2 Master-Agent core ✅** (ADR-029 Accepted, AC-W1-3); **01.3 Billing core ✅** (ADR-008 Wave-1 slice; ЮKassa→01.3b); **01.4 Memory ✅ COMPLETE** — ADR-011 Wave-1 (cell+role memory + conversation history + «запомни»); **01.4b auto-extraction ✅** (filter-agent + LLM summarizer + worker wiring + `memory_curator` archetype; live golden 5/5) | Horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + Telegram Business API |
| Wave 2 (Pixel + каталог) | ⏳ Pending | +WB-Селлер vertical + Pixel + Pyodide + Mini App + Master-Agent first-instances |
| Wave 3 (Глубина) | ⏳ Pending | +ИП-Бух + СМБ-Sales vertical + Vertical Rituals + PARA Workspace |
| Wave 4 (Масштаб) | ⏳ Pending | K8s + Partner programme + Telegram Stars billing |
| Wave 5+ (Enterprise) | ⏳ Pending | On-premise + open marketplace |

## Текущая активная фаза

**Phase 01.4b — Memory auto-extraction (ADR-011 Wave-1 completion)** — ✅ **Code-complete + locally verified + live-validated** (2026-06-24, session `tender-clarke-a1cd06`, branch `claude/tender-clarke-a1cd06`). Закрывает focused-split из 01.4: **автоматический filter-agent** (после `succeeded`-задачи → `memory_entries(source='filter_agent')`) + **LLM conversation summarizer** (overflow → `kind='conversation_summary'`), оба биллятся как `task_steps` через новый горизонтальный **`memory_curator`** archetype (`role_category='analyzer'`, без CHECK-миграции; `step_type='llm_call'`). Orchestrator **`memory_extraction` seam** (зеркало `quota_admission`: default None ⇒ no-op; worker `actor.py` подключает реальный) — на success **pre-final-write**, cost fold в `accumulated_cost` (in-cap, never reject), collision-free `step_index=len(leaf)+2`. Grill (7 forks, 2026-06-24): two agents/`deepseek-chat` · summarizer-impl-only (turn-capture producer → follow-up) · `succeeded`-only · final-deliverable+prompt. **AC-01.4.7 PARTIAL → ✅** (оба триггера) + AC-01.4.6 summarizer-impl ✅. Локальный CI green: mypy --strict **194**, unit **785**, integration **46** (+3 memory: filter→entries, summarize→summary, **billing-invariant `total==SUM(steps)` с новым шагом, no double-count**), `src/memory` 88.77% + новые модули (curator 100% / seed 100% / extraction 99%), bandit 0. **Live golden** `scripts/live_golden_memory.py` **5/5** vs live DeepSeek (~$0.001): rich→`should_remember`+5 typed entries; trivial→`should_remember=false`; summarizer→digest. **Adversarial audit (3 независимых линзы): SOUND / SECURE / NO-REGRESSIONS** 0 P0/P1 — фиксы (content-safe failure log `error_type`; docstring `step_type`; cross-file step-index contract note); 2 pre-existing P2/P3 (`_extract_usage` zero-token; `delete_by_id` defense-in-depth) → chip `task_e980ab7b`. **Deferred (focused-split):** conversation-turn producer + Windows worker-transport live golden (→ CI/Linux, Redis-SSE proven PR #64/#65 + `live_golden_worker_billing.py`). **Founder-action:** merge focused PR → **01.5 Артефакты** (ADR-012).

**Phase 01.4 — Memory (ADR-011 Wave-1)** — ✅ **Code-complete + locally verified** (2026-06-23, session `dazzling-shamir-c26b51`, branch `claude/dazzling-shamir-c26b51`). Двухуровневая memory: **cell memory** + **role memory** (store/search/CRUD API, единая схема `memory` + `cell_id` + FORCE-RLS `current_cell_id()`, **256-dim YandexGPT embeddings** + HNSW cosine, advisory soft caps 500/cell·200/role) + **conversation history** (FIFO N=50 + summarize-on-overflow **seam**) + manual **«запомни»** trigger. Grill-решения (2026-06-23, 7 forks): Q1 **Yandex 256-dim** (ADR's «1024» был неверен; GigaChat embeddings NotImplemented), Q3 **single-schema+RLS** (не per-cell; supersedes неиспользуемый 1024-dim placeholder в `multitenancy/0004`), Q4 retrieval-API-only, Q6 backend+API-only. **Focused-split** (`infra-pr-scope-prefers-focused-splits`): автоматический filter-agent + LLM summarizer + orchestrator post-task wiring → follow-up **`01.4b`** (нужен `agent_archetype_id` seed + hot-path change + flaky-Windows live worker); **AC-01.4.7 PARTIAL** (explicit «запомни» delivered). Локальный CI green: ruff+mypy --strict (**191**), unit **768 passed**, integration **44 passed** (real PG; +4 memory: embedding round-trip + RLS-isolation cell-A↛cell-B + role agent-scoping + conversation FIFO), per-module **memory 88.14%**, bandit 0. **Adversarial-аудит (3 линзы) 0 P0/P1** (SOUND/SECURE/NO-REGRESSIONS; diff purely additive +2261/-0 → billing/runtime untouched). **9 AC-01.4.x green + 1 PARTIAL** (см. [`phases/01.4-memory.md`](./roadmap/wave-1-core-mvp/phases/01.4-memory.md)). **F1 before 01.4:** Master in-process golden re-run **7/7** на funded DeepSeek. **Founder-actions:** merge PR + `01.4b` (auto-extraction) + `01.4-ui` (memory panel) + placeholder-cleanup chip.

**Phase 01.3 — Billing core (ADR-008)** — ✅ **Code-complete + locally verified** (2026-06-22, session `kind-goldstine-ba713f`, branch `claude/kind-goldstine-ba713f`). Account-слой поверх существующего cost-ledger (01.2): `billing.plans` (catalog seed 6 тарифов) + `billing.subscriptions` (RLS по `current_cell_id()`), идемпотентный **Trial 14д/500** грант на register (через `TrialProvisioning` Null-object port в `auth_service.register`), balance/usage-сервисы (SUM по ledger), **агрегатные caps** — per-cell soft-warn→hard-block + per-day hard kill-switch (R-04) на admission задачи (injected `quota_admission` seam в orchestrator), **BYOK plumbing** (skip credit-debit при `byok_key_id` + audit-строка), `/api/v1/billing/{credit-rate,plans,subscription,balance,transactions}`. Grill-решение (2026-06-22): focused split — enforced **Trial+Solo** (Команда = catalog-only, multitenancy single-cell); **ЮKassa → follow-up 01.3b**; rollover/overage deferred. **9 AC-01.3.x green** (см. [`phases/01.3-billing.md`](./roadmap/wave-1-core-mvp/phases/01.3-billing.md)). Локальный CI green: ruff+mypy --strict (175), unit **746 passed**, integration **40 passed** (real PG; +11 billing incl. RLS-isolation + register→trial e2e), per-module **billing 92%** / iam 87% / llm_gateway 89% / runtime 86%, bandit 0. **Adversarial-аудит (3 линзы) 0 P0/P1** (SOUND/SECURE/NO-REGRESSIONS) — поймал реальный баг soft-warn SSE (event_type не в Literal) → фикс + 2 orchestrator seam-теста. **Биллинг-инвариант сохранён:** step-sum = cost authority (без `rollup_task_cost`); sum-check уточнён до managed-only (BYOK строки без debit). **Founder-actions:** merge focused PR + live golden (Docker + funded DeepSeek; `.env` отсутствует в worktree) + OQ-02/OQ-19 → 01.3b.

**Phase 01.2 — Master-Agent core (ADR-029, AC-W1-3)** — ✅ **Code-complete + locally verified** (2026-06-19, session `pedantic-satoshi-8ced82`, branch `claude/pedantic-satoshi-8ced82`). Двухслойная оркестрация для вертикалей: `MasterAgent` (доменный CEO) над `Coordinator` (COO). Реализовано: `StrategicContext` (опц. на `CoordinatorDeps`, горизонталь не тронута) + Coordinator subordinate-retrofit + `MasterAgent` (plan=deepseek-chat → `PlanExecutingCoordinator` → synthesis=R1 → `MasterResponse`); **2-level task-chain** (single budget accumulator → 50-credit cap на Master+children aggregate, R-32/R-04); Marketing-agency РФ reference vertical (seed + Master-prompt AI-baseline `draft` + golden-dataset scaffold). **8 AC-W1-3.x green** (см. [`01.2-master-agent-core.md`](./roadmap/wave-1-core-mvp/phases/01.2-master-agent-core.md)). Локальный CI green: ruff+mypy --strict (163), unit **739 passed** (cov 90.45%), per-module gates agents 98%/runtime 87%/tasks 99%/billing 100%, integration **29 passed** (real PG, +1 Master-billing), bandit 0, drift DRIFT-OK. **Adversarial audit** (Workflow, 17 агентов, 5 линз) → 0 P0/P1, 5 P2 + 3 P3, все устранены (token-rollup, Master pre-call budget gate, budget-metric label, AC-3.2 test). **ADR-029 Proposed → Accepted** (2-level chain + split chat/R1 + reuse `CoordinatorOutput` адаптации). **Founder-actions:** live golden (funded DeepSeek) + evaluator-run для promote Master-prompt `draft → reviewed` (ADR-026). PR против main → founder-merge.

**Phase 01.1-retro (AC-W1 hardening pin block)** — ✅ **VERIFIED-COMPLETE (scoped)** (2026-06-18, session `interesting-knuth-f649a6`). Четыре доменных PR off main **смержены** (`origin/main` = `9aa776f`, база `6b40084` = [PR #53](https://github.com/mrflxxxme/oriion/pull/53)): [#58](https://github.com/mrflxxxme/oriion/pull/58) (AC-W1-8/7/18/17), [#59](https://github.com/mrflxxxme/oriion/pull/59) (AC-W1-10), [#60](https://github.com/mrflxxxme/oriion/pull/60) (AC-W1-4/5), [#61](https://github.com/mrflxxxme/oriion/pull/61) (AC-W1-9 closed-in-code). **Post-merge adversarial аудит объединённого diff** (`6b40084..HEAD`, 48 файлов; 32 агента, 3 линзы + 4 focused-AC, adversarial-verified) → **0 P0 / 4 P1 / 6 P2 / 6 P3**. P1-фиксы внесены (ветка `claude/interesting-knuth-f649a6`): **AC-W1-4 relay был dead-code** → self-rescheduling relay + per-row isolation ([ADR-036](./decisions/ADR-036-outbox-relay-self-scheduling.md)); **AC-W1-9 SIGHUP partial-apply** → DB/Redis cache-reset на refresh; **AC-W1-5** real-PG testcontainers cancel-cascade integration test. Закрыто (verified-in-code): **AC-W1-4/5/7/8/10/17/18 ✅ + AC-W1-9 closed-in-code**. Verified-residual → obs/IaC follow-up: **AC-W1-2** (task_steps таблица-scaffolding, без per-delegation write), **AC-W1-13** (metrics+V4-pricing wired; cost ещё `estimate_credits` + worker-exposition), **AC-W1-14** (bucket-only), **AC-W1-15** (stub receiver). **AC-W1-3** → Wave-2 (ADR-029 Proposed). P2/P3 (10) — backlog в теле PR. Founder-actions: live golden AC8/9/10 (funded keys) + AC-W1-9 staging cutover + `Dockerfile:41` CA-sha256 + PR-merge.

> **🟢 obs/IaC closeout (2026-06-19, session `ecstatic-boyd-7ae652`):** the four verified-residual pins are now **closed + live-proven** in **[PR #66](https://github.com/mrflxxxme/oriion/pull/66)** — **AC-W1-2** (per-delegation `task_steps` write, `task.total==SUM(steps)`), **AC-W1-13** (task cost from `record_llm_cost`/V4 pricing, not the estimate), **AC-W1-14** (Loki S3+90d+compactor + `audit_log` gzip-JSONL cold-archival job), **AC-W1-15** (Alertmanager real Telegram+PagerDuty receivers). Live proof harness `infra/observability/proof/run-proof.sh` **ALL PASS** (chunks→S3 bucket, archival upload round-trip, critical-alert routing). Worker-followups (Prometheus port conflict + `/stream` SSE keep-alive) in **[PR #65](https://github.com/mrflxxxme/oriion/pull/65)**. **Only `AC-W1-3` remains (→ Wave-2, founder decision).** Pending = merge #65 + #66 + deploy-time secret swap (Telegram/PagerDuty/S3 creds via Lockbox) — same boundary as AC-W1-9. Детали — [`HANDOFF.md`](./HANDOFF.md).

**Промежуточный аудит репозитория + remediation** — ✅ **MERGED** ([PR #53](https://github.com/mrflxxxme/oriion/pull/53), `6b40084`, ветка `chore/audit-remediation-w1`, session `adoring-snyder-13a6a3`). P0 green-main ([PR #52](https://github.com/mrflxxxme/oriion/pull/52) merged — TruffleHog gate). Мультиагентный read-only аудит (14 агентов, 4 линзы, adversarial-verified) → 30 находок / 6 P1. Remediation: **6 P1 фиксов** (SSE-IDOR, double-charge, cancel-no-stop, budget-cap, agents-coverage, success-guard) + CI hardening (trivy SHA-pin, codeql v4, setup-uv v6, `.grype.yaml`) + canon-sync (dual-tree guard, ADR-024/027) + **3 chip-PR** ([#54](https://github.com/mrflxxxme/oriion/pull/54) container-hardening, [#55](https://github.com/mrflxxxme/oriion/pull/55) P-AUDIT-3 gate, [#56](https://github.com/mrflxxxme/oriion/pull/56) <500-line refactor). Объединённая ветка зелёная: mypy --strict 154 files, unit 621 / integration 23 / tooling 8, iam 87% / runtime 87.5% после refactor. Детали — [`HANDOFF.md`](./HANDOFF.md).

**Phase 01.1 infra-PR (async-исполнение + наблюдаемость)** — ✅ **MERGED** ([PR #51](https://github.com/mrflxxxme/oriion/pull/51), `fd02473`, 2026-06-17, [ADR-034](./decisions/ADR-034-async-dispatch-redis-sse-ac8-reframe.md) + [ADR-035](./decisions/ADR-035-deepseek-gated-web-search-tool-call.md)). `POST /run` → enqueue Dramatiq actor → **202 <1s**; оркестрация в worker-процессе; SSE через **Redis Streams** (cross-process drain-replay); result в `task.completed` SSE-фрейме (breaking). **AC8 RESOLVED by reframe** (hard-gate = dispatch p95 ≤1s; generation wall-clock ~163s = tracked SLI, per AC-W1-23 + [ADR-025](./decisions/ADR-025-acceptance-gate-format.md) amendment). Закрыто: **AC-W1-16a** (Dramatiq) · **AC-W1-1** (Redis-SSE) · **AC-W1-21** (RU Trusted Root CA в образе + GigaChat verify) · **AC-W1-11** (span header-sanitization) · **AC-W1-12** (thread-safe setup_otel). **AC-W1-19 PARTIAL** (Settings `mock_mode` bug fixed; native DeepSeek-gated tool-call → follow-up). CI green (**588 pass**, mypy --strict 151 files). **Post-merge:** ci-security/TruffleHog сломался на push-to-main (base==head) → исправлен в [PR #52](https://github.com/mrflxxxme/oriion/pull/52) (`a7736a1`, gate TruffleHog к pull_request) — «CI green» actualn на `a7736a1`. **Открытый founder post-merge action:** staging 10× anchor / live-валидация на полном стеке (funded ключи). **Deferred → obs/IaC follow-up PR:** AC-W1-13 (worker-процесс метрики) + AC-W1-2/3/4/5/9/10/14/15.

**Phase 01.1-retro (Track A — Coordinator generalization)** — 🔄 **Code-complete; golden re-run on funded DeepSeek: AC9 ✅ 3/3 + AC10 ✅ 3/3; AC8 ❌ (p95 163s)** (2026-06-15, branch `claude/goofy-darwin-194c68`). Реальный LLM-Координатор по схеме **plan-then-execute / PromptedOutput** ([ADR-032](./decisions/ADR-032-coordinator-plan-then-execute.md)): произвольные промпты, артефакт-тип из плана, code-side framing удалён (AC-W1-24); role-prompts → v1.0.0 + ≥2 non-brief примера/роль (AC-W1-25); single-source role-prompts (AC-W1-20); per-role max_tokens (AC-W1-23a). **AC-W1-16 PARTIAL** (16b done; 16a Dramatiq + AC-W1-1 Redis-SSE → infra-PR). CI green (568 pass, cov 87.9%) + gsd-verifier GOAL ACHIEVED. **Live golden on funded DeepSeek (`sk-69fe…`, `--runs 3`):** ✅ AC9 3/3 (brief 1917-2067w, matrix ≥7×5, content-plan 10/10/10), ✅ AC10 3/3 ($0.026/run), ❌ AC8 cohort p95 **163s > 120s** (analyst+writer long-gen на v4-flash). **2 live-surfaced фикса (PR #44):** provider-timeout 30→120s (`901da5f`) + demo content-plan counter H3-preferred (`b817b73`). **Yandex → Api-Key auth** (`57744ec`, non-expiring; IAM fallback) — live + gateway-smoke 200; GigaChat RU-CA в контейнере = infra-PR. GSD L1 ([ADR-033](./decisions/ADR-033-gsd-methodology-reenablement.md)).

**Phase 00.8 (Design restyling — professional cool-blue v0.2)** — 🔄 **Code-complete; e2e:live pending staging** (2026-06-13 per [ADR-031 Accepted](./decisions/ADR-031-design-direction-restyling.md)). Bake-off → founder выбрал **холодную палитру + Royal Blue `#2563eb`** (отклонил тёплую рамку); tokens v0.2.0 материализованы (deepened cold-slate canvas, info→cyan, on-cta→white, links→cta-hover). AC1/AC2/AC5/AC6 ✓ (lint+build+unit+smoke-axe+toggle green; CI-гейты §A/§B/barrel green). **AC3/AC4 pending:** прогнать `npm run e2e:live` (5-route axe + 3-agent demo) на стенде. Контракт: [`ui/UI-SPEC-00.8.md`](./ui/UI-SPEC-00.8.md). НЕ гейтит D5.

**Session 2026-06-11 (grill-аудит)** — ✅ Complete: 3 быстрых фикса чистоты вывода (role-prompts 0.1.1 в обеих копиях + `normalize_artifact_markdown` в dispatch.py + сворачивание межшаговой аналитики на вкладке «Результат»; backend 50/50, frontend 156/156, lint+build green) + Phase 00.8 + ADR-031 + Pixel-reframing (opt-in skin) + AC-W1-24/25 в 01.1-retro.

**Phase 00.7 (Frontend skeleton)** — ✅ **Complete** (2026-06-11; commit ledger C0–C16). Functional Wave-0 demo UI **live-validated end-to-end** against the real docker stack (register → login → cells → submit «Маркет-бриф» → SSE 3-agent progress → 3 markdown artifacts; `wave-0-demo.spec.ts` @live PASS 2.4min). 18 components, Nordic Warm tokens, axe 0 serious/critical on all 5 routes, cold-start 773ms, coverage 91.8%. 3-agent frontend audit PASS. **AC7 (UI-demo) unblocked.** Spec amendments (no flat `GET /cells`; SSE Bearer-fetch; types from live `/docs`; code-based router) flagged for architect. Deferred polish → [`revisions/00.7-audit-deferred.md`](./revisions/00.7-audit-deferred.md).

**Phase 00.6 PR-B (Stage B + orchestrator-dispatch + live validation)** — ✅ **Complete** ([PR #38](https://github.com/mrflxxxme/oriion/pull/38) C0–C12 + [PR #39](https://github.com/mrflxxxme/oriion/pull/39) C13–C19, merged 2026-06-08). Full 5-agent retro PASS. **Архитектура доказана end-to-end на живом стеке с реальными LLM** (DeepSeek + live Brave + YandexGPT 5.1 Pro failover; AC8+AC10 PASS, AC9 matrix+plan PASS, brief-length = Wave-1 tuning). 7 deployment-багов найдено и починено живым прогоном (C13–C19). См. [`HANDOFF.md`](./HANDOFF.md).

**Оставшийся Wave-0 пункт:** founder staging 10× anchor run (gate D5 — `internal_demo_passed`) — Wave-0→Wave-1 gate, НЕ блокирует Phase 00.7. Runbook: `docs/runbooks/staging-bootstrap.md`.

**Phase 00.6 PR-A (Stage A local infra)** — ✅ **Complete** ([PR #36](https://github.com/mrflxxxme/oriion/pull/36); 22 commits; AC-W1-11..15).

## Phase history (Wave-0)

| Phase | Status | PR | Notes |
|---|---|---|---|
| Pre-Wave-0 roadmap reorg | ✅ Complete | (planning-only) | Session-2026-05-15 — 11 развилок resolved |
| Architect-PR (pre-00.2) | ✅ Complete | [#27](https://github.com/mrflxxxme/oriion/pull/27) | `_shared/0001_init.py` + extended iam contracts + 12 bounded-context migration dirs |
| 00.1 — Repo & CI/CD | ✅ Complete | [#25](https://github.com/mrflxxxme/oriion/pull/25), `b192c6b` | merged 2026-05-17 |
| 00.2 — Custom JWT auth | ✅ Complete | `[00.2] feat(iam)...` 2026-05-18 | src.iam coverage 86.69%, AC1-AC10 green |
| 00.2.5 — Integration | ✅ Complete | [#32](https://github.com/mrflxxxme/oriion/pull/32) 2026-05-19 | 8 commits; deleted `_stubs/` + rewired imports |
| 00.3 — DB+RLS+multitenancy | ✅ Complete | (parallel batch с 00.2 + 00.4) | |
| 00.4 — LLM gateway + MCP | ✅ Complete | (parallel batch с 00.2 + 00.3) | |
| 00.5 / 00.5a — Pydantic-AI runtime | ✅ Complete | merged 2026-05-20 | |
| 00.5b — runtime + tasks + orchestrator | ✅ Complete | [#35](https://github.com/mrflxxxme/oriion/pull/35) 2026-05-21 | 5-agent audit 3H/15M/17L; AC-W1-1..10 pin block |
| **00.6 PR-A** — Stage A local infra | ✅ Complete | [#36](https://github.com/mrflxxxme/oriion/pull/36) 2026-05-25 | 22 commits; self-audit 0H/9M/10L; AC-W1-11..15 pin block extension |
| **00.6 PR-B** — Stage B + orchestrator-dispatch + live validation | ✅ Complete | [#38](https://github.com/mrflxxxme/oriion/pull/38) + [#39](https://github.com/mrflxxxme/oriion/pull/39) 2026-06-08 | C0–C19; 5-agent retro PASS; architecture live-proven; AC-W1-16..23 |
| 00.7 — Frontend skeleton | ✅ Complete | TBD | 2026-06-11; C0–C16; @live demo PASS; 3-agent FE audit PASS; AC7 unblocked; AC1-AC12 (AC4 by-design) |
| 00.8 — Design restyling | 🔄 Code-complete | — | 2026-06-13; cool-blue v0.2 (Royal Blue #2563eb, info→cyan); AC1/2/5/6 ✓; AC3/4 pending `e2e:live` on staging; не гейтит D5 |

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует 01.3 billing-core; gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дней) | Founder + бухгалтер | НЕ блокирует 01.3 billing-core; gates **01.3b ЮKassa** test→live |

> **Note:** OQ-13/14/15/16 (hiring) закрыты как `N/A` per [P-INIT-5](./decisions/ADR-028-policies-registry.md#policies-canonical-home). OQ-17 (funding) + OQ-18 (burn-budget) закрыты как `out-of-scope` per Session-2026-05-15.

## Top-priority risks (active monitoring)

См. [`risks/REGISTER.md`](./risks/REGISTER.md).

1. R-04 (runaway costs) — high + high
2. R-05 (data leak) — critical + medium
3. R-08 (регуляторные изменения) — high + high
4. R-11 (retention/churn) — high + high
5. R-12 (scope creep) — critical + high

## Tech-стек snapshot

Полный список — [`_meta/stack.md`](./_meta/stack.md).

- Backend: Python 3.12 + FastAPI + Pydantic-AI 1.30.1
- Frontend: Vite 6 + React 19 + TanStack Router + Tailwind + shadcn/ui (skeleton in Phase 00.7)
- DB: PostgreSQL 16 + pgvector + Yandex Managed
- Cache: Redis 7 + Dramatiq (orchestrator-dispatch swap к Dramatiq tracked AC-W1-16)
- 2D: Native Canvas
- Code-exec: Pyodide WASM (browser)
- Auth: Custom JWT (W0–1) → Logto (W2–3) → Keycloak (Enterprise)
- LLM: DeepSeek V4-flash/V4-pro (ADR-018 amended in PR-B C6) + YandexGPT + GigaChat + BYOK
- Cloud: Yandex Cloud ru-central-1
- Observability (от Phase 00.6 PR-A): OpenTelemetry SDK + Prometheus 9-metric family + structlog OTel correlation + Loki + Tempo + Grafana 3 dashboards + Alertmanager 8 rules в 3 groups
- IaC (от Phase 00.6 PR-B): Terraform Yandex provider (VM + Managed PG + Redis + Lockbox + DNS + Object Storage)
- CI/CD (от Phase 00.6 PR-B): GitHub Actions deploy-staging workflow (build → push к YC CR → SSH → compose pull/up → wait_healthy → smoke → Grafana annotation, ≤10 min)

## Целевые сроки (revision 2026-05-15)

| Дата | Milestone | Delta vs prior |
|---|---|---|
| 2026-05-17 | Wave 0 Phase 00.1 **started + merged** (2 дня раньше plan) | **-2 нед** |
| 2026-05-26 | Wave 0 Phase 00.6 PR-B **in flight** | on track |
| 2026-06-09 | Wave 0 complete → Internal demo (horizontal `productivity-core`) | unchanged (Phase 00.6 PR-B 10× demo run + Phase 00.7 frontend ship → full anchor flip) |
| 2026-07-21 | Wave 1 complete → Pre-alpha с 10–15 friends (3 templates) | unchanged |
| ~2026-09-22 | Wave 2 complete → Public beta (4 templates + Pixel + Mini App) | **+1 нед** vs prior 2026-09-15 |
| ~2026-12-01 | Wave 3 complete → GA-release (6 templates + Rituals + PARA) | **+3 нед** vs prior 2026-11-10 |
| ~2027-02-22 | Wave 4 complete → Scale + Partner | **+3 нед** vs prior 2027-02-02 |

## Update protocol

При phase complete / blocker resolved / новом ADR:

1. Обновить этот STATUS.md
2. Cross-ref в commit-message: `chore(status): wave 0 phase 00.X complete`
3. Append JOURNAL.md entry для historical record
