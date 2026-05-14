# TEAMLY_RU — Project Entry-Point

**TEAMLY_RU** — облачная платформа AI-команд для СМБ-сегмента РФ. Пользователь нанимает готовую команду одним кликом (5 vertical-templates), Coordinator декомпозирует задачи, агенты выполняют, результат — в Pixel Department.

**USP:** РФ-вертикальная экспертиза (WB-Селлер, Маркетинг-агентство, Telegram-крейтор, ИП-Бухгалтерия, СМБ-Sales).

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
