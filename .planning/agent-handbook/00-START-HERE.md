# 00-START-HERE — Старт сессии для AI-агента

> **Этот файл — protocol для запуска новой AI-агентской сессии.** Гарантирует, что любой agent (Claude, Codex, Cursor, и т.д.) начинает работу с минимальным правильным context'ом и максимальной effectiveness.

## Sequence для новой сессии

### Step 1: Минимальный context-bootstrap (читай в этом порядке)

| # | Файл | Размер | Время |
|---|---|---|---|
| 1 | [`../README.md`](../README.md) | ~3 KB | 30 сек |
| 2 | [`../STATUS.md`](../STATUS.md) | ~4 KB | 1 мин |
| 3 | [`00-START-HERE.md`](./00-START-HERE.md) (этот файл) | ~5 KB | 2 мин |

После этого ты знаешь: что за проект, где мы сейчас, как работать дальше. **Не читай больше пока не понадобится.**

### Step 2: Определи свою роль в текущей задаче

Какая задача поставлена user'ом?

| Тип задачи | Следующий шаг |
|---|---|
| **Имплементация конкретной phase** | Читай [`../roadmap/wave-N/phases/N.M-slug.md`](../roadmap/) |
| **Архитектурное решение** | Читай [`../decisions/README.md`](../decisions/README.md) + relevant ADR |
| **Понять risk/mitigation** | Читай [`../risks/REGISTER.md`](../risks/REGISTER.md) (только нужный R-NN) |
| **Уточнить термин** | Читай [`../_meta/glossary.md`](../_meta/glossary.md) (точечный grep) |
| **Тех. версия / провайдер** | Читай [`../_meta/stack.md`](../_meta/stack.md) (точечный grep) |
| **Сложный multi-step task** | Сначала [`01-CONTEXT-LOADING.md`](./01-CONTEXT-LOADING.md), потом [`02-DELEGATION.md`](./02-DELEGATION.md) |

### Step 3: Загрузи дополнительный context **по мере необходимости**

**НЕ загружай всё превентивно.** Token-budget важен. Принципы:
- Один phase-spec за раз
- ADR — только те, на которые ссылается phase
- Glossary — точечный grep, не full read
- При неоднозначности — [`03-ESCALATION.md`](./03-ESCALATION.md), не строй догадки

## Базовые правила работы

### 1. Уважай существующий стек

Архитектурные решения зафиксированы в 22 ADR. **Не переизобретай**:
- Backend = Python + FastAPI + Pydantic-AI
- Frontend = Vite + React + TanStack
- DB = PostgreSQL + pgvector
- LLM = DeepSeek + YandexGPT + GigaChat (BYOK)
- Auth = Custom JWT (Wave 0-1)
- Pixel = Native Canvas
- Code-exec = Pyodide WASM
- Connectors = MCP-протокол
- Cloud = Yandex Cloud ru-central-1

**Если хочешь отклониться** — создавай новый ADR через template и эскалируй (см. [`03-ESCALATION.md`](./03-ESCALATION.md)).

### 2. TBD-значения — не выдумывай

При встрече identifier'а вида `TBD_OOO_INN` или конфига типа `BRAND_DOMAIN_TBD`:
- Cmotri [`../PLACEHOLDERS.md`](../PLACEHOLDERS.md)
- Используй placeholder как литерал в коде
- НЕ изобретай реальное значение

Подробнее: [`../PLACEHOLDERS.md`](../PLACEHOLDERS.md).

### 3. Делегируй когда возможно

У тебя есть subagents с разными способностями. Используй их (см. [`02-DELEGATION.md`](./02-DELEGATION.md)).

### 4. Спрашивай user'а при неоднозначности

Если решение неочевидно или конфликтует с существующими ADR — [`03-ESCALATION.md`](./03-ESCALATION.md). **Лучше уточнить, чем сделать неправильно.**

### 5. Фиксируй decisions

- Новое архитектурное решение → ADR через [`../decisions/ADR-template.md`](../decisions/ADR-template.md)
- Новый риск → запись в [`../risks/REGISTER.md`](../risks/REGISTER.md) с mitigation
- Новый TBD identifier → в [`../PLACEHOLDERS.md`](../PLACEHOLDERS.md)
- Изменение в phase status → обновить [`../STATUS.md`](../STATUS.md)

### 6. Передавай context при завершении

При окончании session или сложного task — оставь handoff-notes (см. [`04-HANDOFF.md`](./04-HANDOFF.md)).

## Topic shortcuts

- 🚀 «Начинаю работу над phase X» → [`01-CONTEXT-LOADING.md`](./01-CONTEXT-LOADING.md) + соответствующий phase-spec
- 🤝 «Нужно делегировать часть задачи» → [`02-DELEGATION.md`](./02-DELEGATION.md) (11 internal roles + external catalog)
- ❓ «Не понимаю, какое решение правильное» → [`03-ESCALATION.md`](./03-ESCALATION.md)
- 🎯 «Заканчиваю свою часть работы» → [`04-HANDOFF.md`](./04-HANDOFF.md)
- 📝 «Готовлю PR» → [`05-PR-WORKFLOW.md`](./05-PR-WORKFLOW.md)
- 🐛 «Что-то не работает» → [`06-DEBUGGING.md`](./06-DEBUGGING.md)
- ⚙️ «Как работает AI-team pipeline (handoff / failure / cost / Founder approve)» → [`07-AI-TEAM-PIPELINE.md`](./07-AI-TEAM-PIPELINE.md) + [`.claude/AGENTS.md`](../../.claude/AGENTS.md) (entry-point)

## Anti-patterns (НЕ делай так)

### ❌ Загрузка всего проекта сразу
Don't: read all 22 ADR + all phases + all risks в начале сессии.
Do: read README + STATUS + текущий phase-spec. Остальное — JIT.

### ❌ Изобретение конкретных значений для TBD
Don't: пишет `INN = "1234567890"` в коде.
Do: пишет `TBD_OOO_INN` как литерал + ссылку на PLACEHOLDERS.md.

### ❌ Архитектурные decisions без ADR
Don't: меняет database на MongoDB во время phase.
Do: создаёт новый ADR + эскалирует к user'у.

### ❌ Игнорирование existing patterns
Don't: пишет custom auth-flow вместо использования Custom JWT module из ADR-007.
Do: следует ADR-007, использует существующий module.

### ❌ Передача работы без handoff-notes
Don't: завершает session с «всё ок, продолжайте».
Do: оставляет concrete notes о state, blockers, next-steps (см. [`04-HANDOFF.md`](./04-HANDOFF.md)).

## Capabilities reminder

Используй свои tools на полную:

- **Read** — для чтения файлов (с offset/limit для больших)
- **Write/Edit** — для изменений
- **Bash/PowerShell** — для git, build, tests, queries
- **Agent (subagents)** — для делегирования параллельных задач (см. [`02-DELEGATION.md`](./02-DELEGATION.md))
- **Glob/Grep** — для поиска по проекту (быстрее чем читать всё)
- **WebFetch/WebSearch** — для актуальной документации tech-стека (не tribal-knowledge из training)
- **TodoWrite** — для tracking own progress в complex multi-step task
- **mcp__Claude_in_Chrome__\*** — для UI-testing / scrap teamly references

## Финальный checklist для старта

После прочтения этого файла + README + STATUS, ты должен мочь ответить:
- [ ] Что за проект (one-line)?
- [ ] Какая текущая wave / phase?
- [ ] Какие blockers сейчас active?
- [ ] Какой stack для текущей задачи?
- [ ] Куда делегировать если нужно?
- [ ] Как escalate если непонятно?

Если не уверен — перечитай README + STATUS.

**Готов? Начинай работу с конкретного phase-spec или task'а.**
