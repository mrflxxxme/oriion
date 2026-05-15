# verticals/ — Vertical Templates

Vertical-specific артефакты: prompts, golden-dataset, KPI, review-checklists. Один поддиректорий на vertical-template.

> **Revision 2026-05-15:** wave-распределение vertical-templates изменено per [ADR-017 revision](../decisions/ADR-017-vertical-templates.md) + Session-2026-05-15. Каждая vertical-template теперь имеет Master-Agent layer per [ADR-029](../decisions/ADR-029-master-agent-vertical-templates.md). Horizontal preset (`productivity-core`) — отдельная сущность, **не** живёт в `verticals/` (живёт в `contracts/role-prompts/`).

**ADR refs:** [ADR-017](../decisions/ADR-017-vertical-templates.md) (horizontal entry + 5 vertical-templates), [ADR-029](../decisions/ADR-029-master-agent-vertical-templates.md) (Master-Agent layer), [ADR-026](../decisions/ADR-026-vertical-expertise-pipeline.md) (vertical-expertise pipeline), [ADR-010](../decisions/ADR-010-role-versioning.md) (prompt SemVer)

## Catalog distribution (post-Session-2026-05-15)

| Preset | Тип | Wave | Статус | Где живёт |
|---|---|---|---|---|
| `productivity_core` («Твои личные ассистенты») | horizontal | **W0 (anchor)** | active — 4 role-prompts first-draft в Phase 00.5 | [`contracts/role-prompts/`](../contracts/role-prompts/) |
| `agency_marketing_ru` (Маркетинг-агентство РФ) | vertical + Master-Agent | W1 | planned — Master + 2 vertical-specifics в Phase 01.1 | `verticals/marketing-rf/` (TBD W1) |
| `telegram_creator` (Telegram-крейтор) | vertical + Master-Agent | W1 | planned — Phase 01.1 | `verticals/telegram-creator/` (TBD W1) |
| `wb_seller_v1` (WB-Селлер) | vertical + Master-Agent | **W2 (graduated W0→W2)** | deferred prep — see [`wb-seller/`](./wb-seller/) для existing materials (legacy W0-targeting; Wave 2 alignment pending) | [`wb-seller/`](./wb-seller/) |
| `accounting_ip` (ИП-Бухгалтерия) | vertical + Master-Agent | **W3 (graduated W2→W3)** | planned — Phase 03.X | `verticals/ip-accounting/` (TBD W3) |
| `smb_sales_ru` (СМБ-Sales) | vertical + Master-Agent | **W3 (graduated W2→W3)** | planned — Phase 03.X | `verticals/smb-sales/` (TBD W3) |

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
