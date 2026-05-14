# STATUS — текущее состояние проекта

> Rolling-status. Обновляется при phase complete / blocker resolved / новом ADR.

## Wave-progress

| Wave | Status |
|---|---|
| Pre-Wave-0 | 🔄 In progress |
| Wave 0 (Foundation) | ⏳ Pending |
| Wave 1 (Core MVP) | ⏳ Pending |
| Wave 2 (Pixel + каталог) | ⏳ Pending |
| Wave 3 (Глубина) | ⏳ Pending |
| Wave 4 (Масштаб) | ⏳ Pending |
| Wave 5+ (Enterprise) | ⏳ Pending |

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

## Целевые сроки

| Дата | Milestone |
|---|---|
| 2026-05-19 | Wave 0 Phase 00.1 start |
| 2026-06-09 | Wave 0 complete → Internal demo |
| 2026-07-21 | Wave 1 complete → Pre-alpha с 10–15 friends |
| 2026-09-15 | Wave 2 complete → Public beta |
| 2026-11-10 | Wave 3 complete → GA-release |
| 2027-02-02 | Wave 4 complete → Scale + Partner |

## Update protocol

При phase complete / blocker resolved / новом ADR:

1. Обновить этот STATUS.md
2. Cross-ref в commit-message: `chore(status): wave 0 phase 00.1 complete`
