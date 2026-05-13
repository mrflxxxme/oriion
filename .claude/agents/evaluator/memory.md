# Evaluator — memory

## Namespace

`agent-memory:evaluator` (AgentDB, ONNX 384-dim embeddings).

## Что persists

| Entry type | Содержание | TTL |
|---|---|---|
| **known failure pattern** | Pattern (например «coordinator hallucinates WB FBO commission rate когда нет live-data») + reference task-id + recommended probe | До явного resolution в prompt |
| **rubric calibration learning** | Calibration шкалы LLM-as-judge — когда rubric выдаёт false-high / false-low (с примером) | 180 дней |
| **divergence baseline** | Baseline ответов DeepSeek vs YandexGPT vs GigaChat по golden tasks — для divergence-flag detection (Wave 2+) | До major model upgrade |
| **adversarial probe meta** | Какие probe-категории чаще всего ловят regression в каком vertical'е | До явного re-evaluation |

## TTL policy

- Default: 180 дней.
- Hard reset: при upgrade LLM provider (DeepSeek/YandexGPT/GigaChat) major version — все calibration learnings перепроверяются.

## Что НЕ persists

- Конкретные prompt-text snapshots — source-of-truth в `_meta/verticals/<slug>/prompts/`, versioned через git.
- Golden-dataset tasks — source-of-truth в `_meta/verticals/<slug>/golden-dataset/`.
- Cost data — per [P-AUDIT-1](../../../.planning/_meta/GRILL-DECISIONS-ORIION.md).
- Полные run artifacts (raw LLM outputs) — лежат в `.tmp/evaluator-runs/`, expire с phase'ом.
