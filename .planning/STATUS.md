# STATUS — текущее состояние проекта

> Rolling-status. Обновляется при phase complete / blocker resolved / новом ADR.

## Wave-progress

| Wave | Status | Anchor target |
|---|---|---|
| Pre-Wave-0 | 🔄 In progress | Roadmap reorg per [Session-2026-05-15](./JOURNAL.md) |
| Wave 0 (Foundation) | ⏳ Pending | Horizontal `productivity-core` team — internal demo «Market & content brief» |
| Wave 1 (Core MVP) | ⏳ Pending | Horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + Telegram Business API |
| Wave 2 (Pixel + каталог) | ⏳ Pending | +WB-Селлер vertical + Pixel + Pyodide + Mini App + Master-Agent first-instances |
| Wave 3 (Глубина) | ⏳ Pending | +ИП-Бух + СМБ-Sales vertical + Vertical Rituals + PARA Workspace |
| Wave 4 (Масштаб) | ⏳ Pending | K8s + Partner programme + Telegram Stars billing |
| Wave 5+ (Enterprise) | ⏳ Pending | On-premise + open marketplace |

## Recent roadmap revision (2026-05-15)

Per session-decision (11 развилок resolved):

1. Wave 0 anchor: horizontal `productivity-core` team-preset вместо WB-Селлер vertical
2. WB-Селлер вертикаль переезжает Wave 0 → Wave 2 (теперь vertical-anchor для public beta)
3. Wave 1 ships: horizontal + Marketing-agency + Telegram-крейтор (без WB)
4. Wave 2 reduced: ИП-Бух + СМБ-Sales переезжают W2 → W3 (Wave 2 = horizontal + Marketing + Telegram + WB + Pixel + Pyodide + Mini App)
5. Wave 3 grows: +ИП-Бух + СМБ-Sales (+2 нед)
6. Dual messaging positioning: «универсальная команда + РФ-вертикали поверх»
7. Master-Agent layer добавлен для vertical-templates per [ADR-029](./decisions/ADR-029-master-agent-vertical-templates.md)
8. Telegram-mcp v0.2 — Read + post + Business API per [ADR-030](./decisions/ADR-030-telegram-business-api.md) (W1); Mini App W2; Stars billing W4+
9. Deep role prompts для horizontal preset — в [`contracts/role-prompts/`](./contracts/role-prompts/) (first-draft в Phase 00.5, hardening pass в Phase 01.1 retro)

## Текущая активная фаза

**Pre-Wave-0** — подготовка к Phase 00.1 (Repo & CI/CD).

**Следующая phase:** [Phase 00.1 (Repo & CI/CD)](./roadmap/wave-0-foundation/phases/00.1-repo-cicd.md). Owner: DevOps + Tech Lead. Duration: 3 дня.

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-17 | Funding-стратегия | Founder | Required до старта разработки |
| OQ-18 | Burn-бюджет | Founder | Required до старта разработки |
| OQ-04 | РКН-уведомление | Founder + юрист | Required до Phase 00.2 |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa |

> **Note:** OQ-13/14/15/16 (hiring) закрыты как `N/A` per [P-INIT-5](./decisions/ADR-028-policies-registry.md#policies-canonical-home) (solo founder + 11 AI model).

Полный список — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## Top-priority risks (active monitoring)

См. [`risks/REGISTER.md`](./risks/REGISTER.md).

1. R-04 (runaway costs) — high + high
2. R-05 (data leak) — critical + medium
3. R-08 (регуляторные изменения) — high + high
4. R-11 (retention/churn) — high + high
5. R-12 (scope creep) — critical + high

## Tech-стек snapshot

Полный список — [`_meta/stack.md`](./_meta/stack.md).

- Backend: Python 3.12 + FastAPI + Pydantic-AI
- Frontend: Vite 6 + React 19 + TanStack Router + Tailwind + shadcn/ui
- DB: PostgreSQL 16 + pgvector + Yandex Managed
- Cache: Redis 7 + Dramatiq
- 2D: Native Canvas
- Code-exec: Pyodide WASM (browser)
- Auth: Custom JWT (W0–1) → Logto (W2–3) → Keycloak (Enterprise)
- LLM: DeepSeek V3/R1 + YandexGPT + GigaChat + BYOK
- Cloud: Yandex Cloud ru-central-1

## Целевые сроки (revision 2026-05-15)

| Дата | Milestone | Delta vs prior |
|---|---|---|
| 2026-05-19 | Wave 0 Phase 00.1 start | unchanged |
| 2026-06-09 | Wave 0 complete → Internal demo (horizontal `productivity-core`) | unchanged |
| 2026-07-21 | Wave 1 complete → Pre-alpha с 10–15 friends (3 templates) | unchanged |
| ~2026-09-22 | Wave 2 complete → Public beta (4 templates + Pixel + Mini App) | **+1 нед** vs prior 2026-09-15 |
| ~2026-12-01 | Wave 3 complete → GA-release (6 templates + Rituals + PARA) | **+3 нед** vs prior 2026-11-10 |
| ~2027-02-22 | Wave 4 complete → Scale + Partner | **+3 нед** vs prior 2027-02-02 |

## Update protocol

При phase complete / blocker resolved / новом ADR:

1. Обновить этот STATUS.md
2. Cross-ref в commit-message: `chore(status): wave 0 phase 00.1 complete`
