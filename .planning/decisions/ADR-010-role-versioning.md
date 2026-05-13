# ADR-010: Версионирование ролей/templates — SemVer + Canary + Golden dataset

- **Status:** Accepted

## Scope clarification

Versioning per этот ADR применяется к prompt-файлам ролей в `_meta/verticals/<slug>/prompts/<role>.md` (см. [ADR-026](./ADR-026-vertical-expertise-pipeline.md)). Frontmatter contract из ADR-026 включает поле `version: <semver>` — изменения tracked здесь. `role_key` = `<vertical-slug>:<role-name>` (например `wb-seller:coordinator`).

Sprite/archetype IDs (`agent_archetype_id` per [ADR-024](./ADR-024-bounded-context-contracts.md)) — отдельная сущность с собственным versioning через колонку `agents.agent_archetypes.version`. Их жизненный цикл не управляется этим ADR (см. [ADR-021](./ADR-021-ai-generated-pixel-pipeline.md)).

## Decision

### Жизненный цикл версии роли/template

```
draft → staging → canary-5% → canary-25% → stable → deprecated → archived
```

### SemVer-политика

| Тип | Изменения | Rollout |
|---|---|---|
| **patch** (1.2.0 → 1.2.1) | Bug-fix, security, guardrails | Auto всем (после canary) |
| **minor** (1.2.0 → 1.3.0) | Новые tools, расширение scope, стиль | Opt-in с 14-дневным окном предпросмотра |
| **major** (1.x.x → 2.0.0) | Несовместимые изменения, смена модели | Notice 30 дней + сосуществование до 90 дней |

### Canary rollout

- 5% случайных team → 25% → 100%
- Auto-rollback при просадке >10% на 2-часовом окне
- Метрики: success rate, thumbs ratio, retry rate, токены, latency

### Golden dataset

- 50-200 эталонных задач per role/template с reference outputs и rubric'ом
- Любое изменение промпта → прогон → сравнение pass-rate
- Threshold: <5% регрессия = блок выкатки
- Оценка: LLM-as-judge (yandexgpt-lite) + ручной аудит для high-stakes ролей

### Fork-наследование (приватные роли клиента)

- **β:** patch-уровень (security/bugfix) наследуется автоматически
- **γ:** minor/major — уведомление с diff-предпросмотром, opt-in клиента

### Модельный апгрейд

Sonnet 4 → 5, DeepSeek-V3 → V4, и т.п. — всегда **major** для всех ролей, использующих эту модель. Период сосуществования 90 дней.

## Implementation

```
agents.roles_versions
  role_key, version_semver, status, system_prompt, tools[], 
  recommended_model_tier, created_at, deployed_at

agents.canary_assignments
  cell_id, role_key, version_pinned, rollout_bucket (0-99)

agents.golden_datasets
  role_key, dataset_version, tasks_jsonl, rubric_yaml
  
agents.canary_metrics
  role_key, version, metric_name, value, window_start, window_end
```

## Links

- Phase: 02.x (initial role versioning), 02.8 (golden datasets за 11 ролей), 03.x (canary infrastructure)
- Risks: [R-03](../risks/REGISTER.md)
- Related ADRs: ADR-017 (templates), ADR-022 (Coordinator versions), [ADR-024](./ADR-024-bounded-context-contracts.md) (archetype versioning split), [ADR-026](./ADR-026-vertical-expertise-pipeline.md) (vertical-prompts frontmatter contract)
