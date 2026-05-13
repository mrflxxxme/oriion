# Reviewer (frontend) — memory

## Namespace

`agent-memory:reviewer-frontend` (AgentDB, ONNX 384-dim embeddings).

## Что persists

| Entry type | Содержание | TTL |
|---|---|---|
| **recurring violation pattern** | Pattern (например «inline hex в Tailwind config overrides») + frequency + typical fix | 180 дней |
| **false-positive learning** | Случаи когда автоматический check ругался зря (например legit использование `style={{}}` для динамических transform) + reason | До явного re-evaluation |
| **project a11y nuance** | Специфическое для Oriion правило (например «`<dialog>` обязательно с `aria-labelledby`») | До изменения в `_meta/ui/REVIEW-CHECKLIST.md` |
| **revision-loop heuristic** | Знание «implementer X фиксит блокеры с N-й итерации» — позволяет калибровать severity | 90 дней |

## TTL policy

- Default: 90-180 дней.
- Hard reset: при upgrade React / TanStack / shadcn / Tailwind major — memory-curator перепроверяет patterns.

## Что НЕ persists

- Конкретные commit SHAs / file paths review'ов — это `phase-state:<phase-id>`.
- Tokens / inventory snapshots — source-of-truth в `_meta/ui/**`.
- Cost data — per [P-AUDIT-1](../../../.planning/_meta/GRILL-DECISIONS-ORIION.md).
