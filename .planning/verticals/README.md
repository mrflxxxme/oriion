# verticals/ — Vertical Templates

Vertical-specific артефакты: prompts, golden-dataset, KPI, review-checklists. Один поддиректорий на vertical-template.

**ADR refs:** [ADR-017](../decisions/ADR-017-vertical-templates.md) (5 vertical-templates), [ADR-026](../decisions/ADR-026-vertical-expertise-pipeline.md) (vertical-expertise pipeline), [ADR-010](../decisions/ADR-010-role-versioning.md) (prompt SemVer)

## Vertical-templates

| Вертикаль | Wave | Статус |
|---|---|---|
| [`wb-seller/`](./wb-seller/) | Wave 0 (foundation) | active — prompts + golden-dataset draft |
| marketing-rf | Wave 1 | planned |
| telegram-creator | Wave 1 | planned |
| ip-accounting | Wave 2 | planned |
| smb-sales | Wave 2 | planned |

## Структура одной вертикали

```
<slug>/
├── README.md              ICP, JTBD, KPIs
├── domain-glossary.md     термины вертикали
├── workflow-dag.md        agent interaction DAG
├── prompts/               role prompts (SemVer per ADR-010)
├── golden-dataset/        30 tasks + adversarial probes
├── REVIEW-CHECKLIST.md    founder review gate
├── kpis.md                business metrics
└── changelog.md           prompt regression tracking
```

## Validation gate

Promote vertical `draft` → `reviewed` → `locked` per ADR-026 §5:
- ≥75% pass-rate на golden-dataset
- 100% pass-rate на adversarial probes
- Founder REVIEW-CHECKLIST подписан
