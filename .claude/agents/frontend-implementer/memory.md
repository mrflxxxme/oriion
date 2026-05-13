# Frontend implementer — memory

## Namespace

`agent-memory:frontend-implementer` (AgentDB, ONNX 384-dim embeddings).

## Что persists

| Entry type | Содержание | TTL |
|---|---|---|
| **reusable hook/util** | Имя + path + signature + use-case (например `useDebouncedFilter` для tables) | До deprecation в codebase |
| **repo convention** | Локальное соглашение (например «все routes в TanStack используют `loader` not `useQuery` для initial data») | До явного override в conventions.md |
| **recurring lint-fix pattern** | Pattern + автоматический fix (например react-hooks/exhaustive-deps в специфичных случаях) | 60 дней |
| **revision-feedback lesson** | Конкретный reviewer-feedback + как зафиксил + how-to-avoid | 90 дней |

## TTL policy

- Default: 60-90 дней.
- Hard reset: при upgrade major React / TanStack / shadcn / Tailwind версии — memory-curator перепроверяет relevance всех записей.

## Что НЕ persists

- Specifics phase'а (file lists, commit SHAs) — это `phase-state:<phase-id>`, не agent-memory.
- Tokens / colors / spacing — source-of-truth в `_meta/ui/design-tokens.md`, дублирование запрещено.
- Cost data — per [P-AUDIT-1](../../../.planning/_meta/GRILL-DECISIONS-ORIION.md).
