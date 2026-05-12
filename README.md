# TEAMLY_RU — AI-Agent Project Entry-Point

> **Первый файл, который AI-агент читает в новой сессии.** ~3 KB context → точки навигации ко всему остальному.

## Что это за проект

**TEAMLY_RU** — облачная платформа AI-команд для СМБ-сегмента РФ. Пользователь нанимает готовую команду одним кликом (5 vertical-templates), Coordinator декомпозирует задачи, агенты выполняют, результат — в Pixel Department.

**Primary USP:** РФ-вертикальная экспертиза (WB-Селлер, Маркетинг-агентство, Telegram-крейтор, ИП-Бухгалтерия, СМБ-Sales).

**LLM-стек (Wave 0):** DeepSeek V3/R1 (premium) + YandexGPT + GigaChat (RU), все BYOK с дня 1.

**Tech-стек MVP:** Python + FastAPI + Pydantic-AI (backend) + Vite + React + TanStack (frontend) + Native Canvas 2D (Pixel) + PostgreSQL + pgvector + Yandex Cloud.

## Навигация

### Начинаю новую AI-агентскую сессию

1. README.md (этот файл)
2. [`STATUS.md`](./STATUS.md) — текущее состояние проекта
3. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow для AI-агентов
4. [`PLACEHOLDERS.md`](./PLACEHOLDERS.md) — реестр TBD-значений (читать **только** при встрече placeholder)

### Работа над конкретной фазой

1. [`roadmap/INDEX.md`](./roadmap/INDEX.md) — карта Wave / Phase
2. [`roadmap/wave-N/README.md`](./roadmap/) — обзор волны
3. [`roadmap/wave-N/phases/N.M-slug.md`](./roadmap/) — spec фазы

### Reference (точечный grep, не full-read)

- Термин → [`_meta/glossary.md`](./_meta/glossary.md)
- Tech-версия / провайдер → [`_meta/stack.md`](./_meta/stack.md)
- Code/process-convention → [`_meta/conventions.md`](./_meta/conventions.md)
- Архитектурное решение → [`decisions/`](./decisions/)
- Риск → [`risks/REGISTER.md`](./risks/REGISTER.md)

### Workflow questions

- Делегирование → [`agent-handbook/02-DELEGATION.md`](./agent-handbook/02-DELEGATION.md)
- Когда спросить user'а → [`agent-handbook/03-ESCALATION.md`](./agent-handbook/03-ESCALATION.md)
- Передача context → [`agent-handbook/04-HANDOFF.md`](./agent-handbook/04-HANDOFF.md)
- PR workflow → [`agent-handbook/05-PR-WORKFLOW.md`](./agent-handbook/05-PR-WORKFLOW.md)
- Debugging → [`agent-handbook/06-DEBUGGING.md`](./agent-handbook/06-DEBUGGING.md)

## Структура `.planning/`

```
.planning/
├── README.md                       AI-agent entry-point
├── STATUS.md                       текущий статус + blockers
├── PROJECT.md                      project overview
├── PLACEHOLDERS.md                 реестр TBD-значений
│
├── agent-handbook/                 инструкции для AI-агентов (7 файлов)
├── _meta/                          reference: stack, glossary, conventions, OQ
├── decisions/                      22 ADR
├── risks/                          REGISTER (открытые риски)
└── roadmap/                        Wave 0–5+ с phases
```

## Базовые правила

1. **JIT context-loading** — читай только необходимое. README + STATUS + текущий phase-spec = достаточно для 80% задач.
2. **Делегируй subagent'ам** ([`agent-handbook/02-DELEGATION.md`](./agent-handbook/02-DELEGATION.md)).
3. **Спрашивай при неоднозначности** ([`agent-handbook/03-ESCALATION.md`](./agent-handbook/03-ESCALATION.md)).
4. **TBD-tokens** — не выдумывай реальные значения, цитируй [`PLACEHOLDERS.md`](./PLACEHOLDERS.md).
5. **При завершении задачи** — обнови [`STATUS.md`](./STATUS.md) + phase-checkpoints.
6. **Новые решения** — через ADR template.

## Context priority

| Priority | Файл | Когда |
|---|---|---|
| P0 | README + STATUS | Всегда (1×/session) |
| P1 | Текущий phase-spec + 00-START-HERE | Task-start |
| P2 | Цитируемые ADR / risks | On reference |
| P3 | glossary / stack / conventions | On lookup (grep, не full-read) |
| P4 | Other ADR / phases | Rare |

**Typical session budget:** ~15–30 KB context loaded, ~80–100 KB available для работы.
