# Oriion — Project Entry-Point

**Oriion** (рабочее имя per [ADR-040 D3](./decisions/ADR-040-execution-spec-contract.md); прежнее TEAMLY_RU, финальный бренд — OQ-09) — облачная платформа AI-команд для СМБ + personal-users сегмента РФ. Пользователь стартует с универсальной команды («Твои личные ассистенты»), при необходимости расширяет до vertical-команды с domain-expertise. Coordinator декомпозирует задачи (или Master-Agent в vertical-режиме per [ADR-029](./decisions/ADR-029-master-agent-vertical-templates.md)), агенты выполняют, результат — в Pixel Department.

**USP (dual messaging, per [Session-2026-05-15](./JOURNAL.md)):**
- **Entry:** универсальный horizontal preset `productivity-core` («Твои личные ассистенты»)
- **Depth:** 5 РФ-vertical-templates (Маркетинг-агентство, Telegram-крейтор, WB-Селлер, ИП-Бухгалтерия, СМБ-Sales) с Master-Agent layer

**Tech-стек (Wave 0):** Python + FastAPI + Pydantic-AI · Vite + React + TanStack · PostgreSQL + pgvector · Native Canvas 2D · DeepSeek/YandexGPT/GigaChat (BYOK) · Yandex Cloud. Версии — [`_meta/stack.md`](./_meta/stack.md).

## Структура `.planning/`

```
.planning/
├── README.md            ← этот файл (что за проект)
├── STATUS.md            ← активная phase + блокеры (rolling)
├── HANDOFF.md           ← снимок от прошлой сессии
├── JOURNAL.md           ← append-only лог сессий (внутренний)
├── PROJECT.md           ← USP, команда, vertical-templates
├── PLACEHOLDERS.md      ← реестр TBD-значений
├── OPEN-QUESTIONS.md    ← открытые founder-вопросы
│
├── agent-handbook/      ← workflow для AI-агентов (entry: 00-START-HERE.md)
├── decisions/           ← ADR-каталог (entry: README.md)
├── risks/               ← REGISTER + README
├── roadmap/             ← Wave 0–5+ (entry: README.md)
│
├── contracts/           ← bounded-context API/data контракты
├── verticals/           ← vertical prompts + golden-dataset
├── ui/                  ← UI design system
├── tools/               ← MCP tool registry
│
├── gates/               ← wave-gate критерии
└── _meta/               ← короткие справочники (stack, glossary, conventions)
```

## AI-агент: следующий шаг

**Читай:** [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — там жёсткий bootstrap-чек-лист и протокол работы.

## Навигация по папкам

Каждая папка содержит свой `README.md` как entry-point. Заходя в `.planning/X/` — сначала читай `X/README.md`.
