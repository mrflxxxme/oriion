# Designer — memory

## Namespace

`agent-memory:designer` (AgentDB, ONNX 384-dim embeddings, DiskANN/HNSW vector search).

## Что persists

| Entry type | Содержание | TTL |
|---|---|---|
| **vetted component pattern** | Конкретное использование компонента из inventory с подтверждённым tokens-set, screenshot для reference | 90 дней или до token-update |
| **design-token decision** | Решение «использовать `amber-500` для primary CTA вместо `amber-600`» с justification + phase-id | До явного founder override |
| **rejected mock** | Mock + reason rejection (reviewer-frontend feedback / founder reject / a11y fail) | 90 дней |
| **inventory-patch proposal** | Предложенный новый вариант компонента + статус (pending/approved/rejected founder) | До resolve статуса |

## TTL policy

- Default: 90 дней (per DECISION-4 — design-system итерационная, старые решения теряют актуальность).
- Hard reset: любой commit, меняющий `_meta/ui/design-tokens.md`, триггерит memory-curator перепроверить relevance всех `vetted component pattern` записей.

## Что НЕ persists

- Mock binaries (PNG/HTML) — лежат в `_meta/ui/reference-screens/` или `.tmp/mocks/`, не дублируются в memory.
- Раw `ui-spec:` секции phase-spec'ов — source-of-truth остаётся в phase-файле.
- Cost/budget данные — per [P-AUDIT-1](../../../.planning/_meta/GRILL-DECISIONS-ORIION.md).
