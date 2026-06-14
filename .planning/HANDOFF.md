# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-15 (Phase 01.1-retro **Track A — Coordinator generalization**: execute)
- Session: `goofy-darwin-194c68`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. Phase 01.1 **Track A code-complete** (9 атомарных коммитов C1–C9 off `d86b3ba`). CI-deterministic green; **live golden pending founder** (нет BYOK-`.env` в worktree).
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

- **CI-deterministic (green, без ключей):** backend `ruff` + `ruff format --check` ✓; `mypy --strict` (145 files) ✓; `pytest` **567 passed, 23 deselected (@live), cov 87.9%** ✓; role-prompt drift-check (`diff -rq` canonical vs synced) ✓; frontend `TaskSubmitPage` 5/5 + prettier + eslint ✓.
- **gsd-verifier (GSD L1) — GOAL ACHIEVED:** все 6 in-scope AC verified. Минорные не-блокеры (учтены): canned writer-fixture рендерит контент-план нумерованным списком, а не `### Пост N`-заголовком (CI self-consistent; **реальную форму проверяет только live**).
- **Pending — live golden (founder-action, нет `.env`):** real DeepSeek/Yandex BYOK на локальном docker.

## Next actions

1. **Founder: провизионить `backend/.env`** (DeepSeek + YandexGPT/GigaChat ключи, как в Phase 00.6 PR-A — gitignored, per-worktree).
2. **Live golden-прогон** из repo root:
   ```sh
   sh scripts/sync_role_prompts.sh
   docker compose -f infra/docker-compose.staging.yml -f infra/docker-compose.staging-local.override.yml --env-file backend/.env up -d --build
   python -m scripts.demo_market_brief --api-base-url http://localhost:8000/api/v1 --jwt $DEMO_JWT --cell-id $DEMO_CELL_ID --runs 3 --output .tmp/golden/
   ```
   Assert: `delegation_plan` от реального Координатора (3 шага); AC9 (brief ≥1500 слов, матрица ≥5×4, 10 постов `### Пост N — <канал> — <день>`); AC10 (≤0.30 USD/run); AC8 (cohort p95 ≤120s); SSE-леджер `started → 3×(deleg) → completed`.
3. **★ Главная live-проверка (gsd-verifier):** прогнать **non-market-brief** промпт через frontend (напр. «Перепиши лендинг и сделай 3 A/B-варианта заголовка») → fenced-JSON план парсится в `CoordinatorOutput`, `artifact_type` осмыслен под intent (напр. `landing-copy`, не `brief`), прозы вокруг JSON нет (парсер строгий). Заодно глазами: writer реально эмитит `### Пост N`-заголовки.
4. **Merge PR** (verify-bar = CI + live golden, per founder grill-decision).
5. **Infra-PR (следующий):** AC-W1-16a (Dramatiq actor) + AC-W1-1 (Redis-pubsub SSE) + AC-W1-19 (native web_search tool) + observability/IaC-пины (3/4/5/9/10/11-15/21).
6. **GSD L2 spike** (отдельно): ROADMAP.md + config.json + `/gsd:health --repair` + layout-bridge.

## Exit ritual (this session)

- [x] ADR-032 (plan-then-execute) + ADR-033 (GSD L1/L2) созданы; decisions/README + ADR-023 §6 correction-note
- [x] JOURNAL.md — 2026-06-15 goofy-darwin entry
- [x] STATUS.md — Wave 1 in-progress + 01.1 Track A active-phase
- [x] HANDOFF.md rewritten (this file)
- [x] CI-deterministic green + gsd-verifier GOAL ACHIEVED
- [ ] live golden + non-brief submit (founder, нужен `.env`)
- [ ] PR merge
