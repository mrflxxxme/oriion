# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-15 (Phase 01.1-retro **Track A** — funded-DeepSeek live validation + 2 live-surfaced fixes)
- Session: `goofy-darwin-194c68` (continued)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. Phase 01.1 **Track A code-complete** (C1–C9 + live-fixes). CI-deterministic green (568 passed); **core live-validated** (PromptedOutput + генерализация); **market-brief golden re-run on funded DeepSeek: AC9 ✅ 3/3 + AC10 ✅ 3/3; AC8 ❌ (cohort p95 163s > 120s — DeepSeek v4-flash long-gen latency, infra-PR perf item).**
- **Phase 01.1 Track A scope:** AC-W1-16b ✅, AC-W1-24 ✅, AC-W1-25 ✅, AC-W1-20 ✅, AC-W1-22 ✅, AC-W1-23a ✅. **AC-W1-16 PARTIAL** — 16b (реальный Координатор) done; **16a (Dramatiq 202<1s) + AC-W1-1 (Redis-SSE) → infra-PR.**
- **Phase 00.8 (design restyling):** code-complete, e2e:live pending staging (independent, не блокирует 01.1).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Wave 1) |

## What just happened — Phase 01.1 Track A (2026-06-15)

Founder-process: bootstrap-4 → `/grill-me` (8 развилок) → Plan-агент → execute (C1–C9) → `gsd-verifier` (GSD L1) → exit ritual.

### Ключевое решение ([ADR-032](./decisions/ADR-032-coordinator-plan-then-execute.md))
Координатор решает декомпозицию **plan-then-execute через Pydantic-AI `PromptedOutput`**, НЕ native tool-call (отклонение от буквы AC-W1-16, зафиксировано). Причина: `deepseek-reasoner` не умеет tools/JSON; только DeepSeek форвардит tools (Yandex/GigaChat — нет → native loop ломает failover). Plain-text in/out → робастно на всех 3 провайдерах; **gateway tool-forwarding = 0**.

### Код (9 коммитов, verified green)
- **C1** `pydantic_ai_model.py` — `request()` → `prepare_request` + инъекция `prompted_output_instructions` системным сообщением.
- **C2** `agents/coordinator.py` — `PromptedOutput(CoordinatorOutput)`, `tools=[]`.
- **C3** `router_service.py` — coordinator→`deepseek-chat`. **C4** — `ROLE_TO_MAX_TOKENS` (coord 2048 / r,a 4096 / writer 8192).
- **C5** `runtime/dispatch.py` — `PlanExecutingCoordinator` (план→исполнение через orchestrator runner; guard'ы через `assert_delegation_allowed`; `DelegationStep.artifact_type`); удалены `_SUB_PROMPT_FRAMING`/`DEFAULT_PIPELINE`/`_ARTIFACT_KIND`/`ScriptedCoordinator`.
- **C6** canned coordinator fixture → один fenced-JSON план + real-path demo-flow тест.
- **C7** role-prompts → v1.0.0/stable; Координатор §1/§2/§3/§6 → JSON-план output; r/a/w +≥2 non-brief §6-примера.
- **C8** single-source: `scripts/sync_role_prompts.{sh,ps1}` + `backend/.gitignore` + CI drift-check; committed `backend/role_prompts/` дубль удалён.
- **C9** frontend `TaskSubmitPage` пресет несёт полный AC9-контракт; backend prompt-agnostic + `demo_market_brief.py` DEMO_PROMPT синхронизирован.

### Доки
- **ADR-032** (plan-then-execute, Accepted) + **ADR-033** (GSD re-enablement L1/L2, Proposed; correction-note к ADR-023 §6). decisions/README обновлён.
- STATUS / JOURNAL обновлены.

### GSD (per [ADR-033](./decisions/ADR-033-gsd-methodology-reenablement.md))
**L1 восстановлен и продемонстрирован:** `gsd-verifier` прогнан goal-backward на Track A → **verdict GOAL ACHIEVED**. **L2** (slash-оркестраторы: ROADMAP.md/STATE.md/config.json/layout-bridge) — отдельный planning-spike, НЕ в этом PR.

## Verification state

- **CI-deterministic (green):** backend `ruff` + `ruff format --check` ✓; `mypy --strict` (145 files) ✓; `pytest` **568 passed, 23 deselected (@live), cov 87.9%** ✓; role-prompt drift-check ✓; frontend `TaskSubmitPage` 5/5 + prettier + eslint ✓.
- **gsd-verifier (GSD L1) — GOAL ACHIEVED:** все 6 in-scope AC verified.
- **Live-валидация (2026-06-15, локальный `oriion_live` стек):** ключи `.env` из `great-engelbart` worktree. DeepSeek **402** (out-of-balance), YandexGPT **401** (IAM-токен 2026-05-25 истёк) → failover на **GigaChat**.
  - ✅ **PromptedOutput на реальном LLM:** GigaChat вернул schema-conformant JSON → распарсилось в `CoordinatorOutput`. Центральный риск verifier'а (fenced-JSON на реальном провайдере) — снят.
  - ✅ **Генерализация (AC-W1-24):** тривиальный + «сравни 3 CRM» → **direct-action** (пустой план); «перепиши лендинг» → **writer-only** план, `artifact_type="copywriting"` (НЕ `brief`).
  - ✅ **Fix surfaced live → commit `193a1fc`:** GigaChat 422 на двух system-message (PromptedOutput добавляет 2-й) → `_messages_to_openai_shape` мёржит в один → **200** ([ADR-032](./decisions/ADR-032-coordinator-plan-then-execute.md) §Validated live).
  - ⚠️ **Market-brief AC8/9/10 НЕ закрыт:** GigaChat ReadTimeout'ит на ≥1500-словном writer (30s per-call provider timeout) + не уложится в AC8 latency. **Нужен funded DeepSeek** (быстрый primary).

## Next actions

1. **✅ DONE — DeepSeek funded + wired.** New funded key `sk-69fe…358ab` (USD $6.93, `is_available:true`) in `backend/.env`; live-verified HTTP 200 for `deepseek-chat`/`reasoner`/`v4-flash`. Market-brief golden re-run on it (below).
2. **⚠️ Yandex still blocked (founder action).** Balance fixed by founder, but the `.env` IAM token is **time-expired** (2026-05-26) AND the local `yc` CLI's own OAuth is expired → cannot mint a replacement non-interactively. **Unblock:** run `yc init` (browser re-auth) on the dev box, then `yc iam create-token --impersonate-service-account-id ajen5nokvbqalrt97tbd` → paste into `YANDEX_IAM_TOKEN`. Failover-only — does **not** block the DeepSeek-primary golden.
3. **✅ Market-brief golden re-run (funded DeepSeek, `--runs 3`, 2026-06-15):** **AC9 ✅ 3/3** (brief 2067/1917/1954w; matrix 7×5/7×5/7×6; content-plan 10/10/10), **AC10 ✅ 3/3** ($0.026/run). **AC8 ❌** — cohort p95 **163s > 120s** (analyst ~45s + writer ~46s long-gen on v4-flash dominate). Two live-surfaced fixes committed: provider-timeout 30→120s + demo content-plan counter (H3-preferred). **AC8 decision pending founder** (faster model / pipeline-parallelism = infra-PR, OR accept latency latitude).
4. **Merge [PR #44](https://github.com/mrflxxxme/oriion/pull/44):** verify-bar = CI ✅ (568) + golden AC9/AC10 ✅; **AC8 latency is the remaining founder call** per ADR-027.
4. **Infra-PR (следующий):** AC-W1-16a (Dramatiq) + AC-W1-1 (Redis-SSE) + AC-W1-19 (native web_search) + observability/IaC-пины (3/4/5/9/10/11-15/21). **+ live-surfaced:** per-provider httpx-timeout (GigaChat медленный на long-gen — 30s мало) + GigaChat RU-CA в образе (AC-W1-21).
5. **GSD L2 spike** (отдельно): ROADMAP.md + config.json + `/gsd:health --repair` + layout-bridge.

## Exit ritual (this session)

- [x] ADR-032 (plan-then-execute) + ADR-033 (GSD L1/L2) созданы; decisions/README + ADR-023 §6 correction-note
- [x] JOURNAL.md — 2026-06-15 goofy-darwin entry
- [x] STATUS.md — Wave 1 in-progress + 01.1 Track A active-phase
- [x] HANDOFF.md rewritten (this file)
- [x] CI-deterministic green (568) + gsd-verifier GOAL ACHIEVED
- [x] Live-валидация: PromptedOutput + генерализация на GigaChat ✓; multi-system merge-fix (commit `193a1fc`)
- [x] market-brief golden on **funded DeepSeek** (`--runs 3`): **AC9 ✅ 3/3 + AC10 ✅ 3/3**; **AC8 ❌** (p95 163s)
- [x] live-surfaced fixes committed: provider-timeout 30→120s (`config.py`+`main.py`) + demo content-plan counter H3-preferred
- [x] CI-deterministic re-green with fixes: ruff/mypy(145)/pytest **568 passed**
- [ ] **Yandex IAM** refresh (founder: `yc init` → mint token) — failover-only
- [ ] **AC8 latency** decision (founder: faster model / pipeline-parallel = infra-PR, or accept latitude)
- [ ] PR merge (founder, per ADR-027)
