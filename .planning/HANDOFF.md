# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-15 (Phase 01.1-retro **Track A — Coordinator generalization**: execute)
- Session: `goofy-darwin-194c68`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. Phase 01.1 **Track A code-complete** (C1–C9 + live-fix off `d86b3ba`). CI-deterministic green; **core live-validated на GigaChat** (PromptedOutput + генерализация); market-brief AC8/9/10 pending **funded DeepSeek** (текущий ключ 402 out-of-balance).
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

1. **Founder: пополнить DeepSeek-баланс** (сейчас 402 out-of-balance) и/или обновить YandexGPT IAM-токен (`yc iam create-token` → `YANDEX_IAM_TOKEN` в `backend/.env`; текущий от 2026-05-25 истёк). Ключи аутентифицируются, но DeepSeek без денег + Yandex IAM протух → live шёл через GigaChat.
2. **Закрыть market-brief AC8/9/10 на funded DeepSeek** (быстрый primary — без GigaChat ReadTimeout'ов):
   ```sh
   uv run python -m scripts.demo_market_brief --api-base-url http://localhost:8001/api/v1 \
     --jwt <fresh-login-token> --cell-id <cell> --runs 3 --output .tmp/golden/
   ```
   Core-тезис (PromptedOutput-парсинг + генерализация Координатора) **уже live-validated** на GigaChat (см. Verification state); осталась только market-brief content-shape (AC9) + latency (AC8) на DeepSeek.
3. **Merge [PR #44](https://github.com/mrflxxxme/oriion/pull/44)** (verify-bar = CI + market-brief golden на DeepSeek). Founder-merge per ADR-027.
4. **Infra-PR (следующий):** AC-W1-16a (Dramatiq) + AC-W1-1 (Redis-SSE) + AC-W1-19 (native web_search) + observability/IaC-пины (3/4/5/9/10/11-15/21). **+ live-surfaced:** per-provider httpx-timeout (GigaChat медленный на long-gen — 30s мало) + GigaChat RU-CA в образе (AC-W1-21).
5. **GSD L2 spike** (отдельно): ROADMAP.md + config.json + `/gsd:health --repair` + layout-bridge.

## Exit ritual (this session)

- [x] ADR-032 (plan-then-execute) + ADR-033 (GSD L1/L2) созданы; decisions/README + ADR-023 §6 correction-note
- [x] JOURNAL.md — 2026-06-15 goofy-darwin entry
- [x] STATUS.md — Wave 1 in-progress + 01.1 Track A active-phase
- [x] HANDOFF.md rewritten (this file)
- [x] CI-deterministic green (568) + gsd-verifier GOAL ACHIEVED
- [x] Live-валидация: PromptedOutput + генерализация на GigaChat ✓; multi-system merge-fix (commit `193a1fc`)
- [ ] market-brief AC8/9/10 на funded DeepSeek (founder billing action)
- [ ] PR merge (founder, per ADR-027)
