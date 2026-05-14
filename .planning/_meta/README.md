# _meta/ — Reference Library

Короткие справочники проекта. Точечный grep, не full-read.

## Файлы

| Файл | Содержание | Когда читать |
|---|---|---|
| [`stack.md`](./stack.md) | Полный технический стек (backend/frontend/db/llm), версии, провайдеры | Когда нужна tech-версия или provider-config |
| [`glossary.md`](./glossary.md) | Словарь домена (Cell, Vertical-template, BYOK, Rituals, MCP, …) | При встрече незнакомого термина |
| [`conventions.md`](./conventions.md) | Code-style, tier-review, CI gates, definition of done | При создании кода / PR |

## Quick-lookups

- Версия библиотеки → `Grep(pattern="React", path="_meta/stack.md")`
- Определение термина → `Grep(pattern="^\\| \\*\\*Cell\\*\\*", path="_meta/glossary.md")`
- Convention для X → grep `conventions.md` по теме (lint, test, branch, commit, PR)

## Anti-patterns

- ❌ Full-read всех `_meta/*` в начале сессии — это P3 в context priority (см. [`agent-handbook/00-START-HERE.md`](../agent-handbook/00-START-HERE.md))
- ❌ Дублирование содержимого из `_meta/*` в phase-файлы — лучше cross-ref

## Что НЕ здесь (поднято на верхний уровень `.planning/`)

- [`../contracts/`](../contracts/) — bounded-context API/data контракты
- [`../verticals/`](../verticals/) — vertical-specific prompts + golden-dataset
- [`../ui/`](../ui/) — UI design system
- [`../tools/`](../tools/) — MCP tool registry
- [`../OPEN-QUESTIONS.md`](../OPEN-QUESTIONS.md) — открытые founder-вопросы (state)
