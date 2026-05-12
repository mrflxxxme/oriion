# _meta/ — Reference Index

> Точечная навигация по reference-файлам. Используй grep, не full-read.

## Файлы

| Файл | Что внутри | Когда использовать |
|---|---|---|
| [`stack.md`](./stack.md) | Полный технический стек (backend/frontend/db/llm/etc.), версии, провайдеры | Когда нужна tech-версия или provider-config |
| [`glossary.md`](./glossary.md) | Словарь домена (Cell, Vertical-template, BYOK, Rituals, MCP, и т.д.) | При встрече незнакомого термина |
| [`conventions.md`](./conventions.md) | Code-style, tier-review, CI gates, definition of done | При создании кода / PR |
| [`agent-protocol.md`](./agent-protocol.md) | Протокол работы AI-агентов (предыстория handbook'а) | Дополняется [`../agent-handbook/`](../agent-handbook/) |
| [`open-questions.md`](./open-questions.md) | Open Questions для founder-decision | При encounter blocker / TBD |

## Quick-lookups

### Какая версия X?

→ grep `stack.md`:
```
Grep(pattern="React", path="_meta/stack.md", output_mode="content")
Grep(pattern="FastAPI", path="_meta/stack.md", output_mode="content")
```

### Что означает термин X?

→ grep `glossary.md`:
```
Grep(pattern="^\\| \\*\\*Cell\\*\\*", path="_meta/glossary.md")
```

### Какая convention для X?

→ grep `conventions.md` по теме (lint, test, branch, commit, PR)

### Какой OQ закрыт / открыт?

→ `open-questions.md` — таблицы с status

### Где cross-references?

- **stack.md → ADR:** каждая tech-выборка ссылается на ADR
- **glossary.md → ADR:** каждый ключевой термин cross-ref
- **conventions.md → ADR-015** (AI-dev process)
- **open-questions.md → SYNTHESIS** + grill

## Anti-patterns

- ❌ Full-read всех `_meta/*` в начале сессии (P3 в [`agent-handbook/01-CONTEXT-LOADING.md`](../agent-handbook/01-CONTEXT-LOADING.md))
- ❌ Дублирование содержимого из `_meta/*` в phase-файлы — лучше cross-ref
- ❌ Изменение `_meta/*` без cross-ref в commit-message
