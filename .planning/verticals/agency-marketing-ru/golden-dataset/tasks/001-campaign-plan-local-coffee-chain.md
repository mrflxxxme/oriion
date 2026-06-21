---
id: 001
slug: campaign-plan-local-coffee-chain
difficulty: easy
primary_task: campaign-planning
agent_archetype: master-agency-marketing-ru
archetype_path: master → coordinator → researcher/analyst/writer
created_by: ai-baseline
created_at: 2026-06-19
adversarial: false
last_evaluated: null
---

# Task 001 — Quarterly campaign plan for a local coffee chain (demo scenario)

## Input

```json
{
  "task_type": "campaign-planning",
  "client": "Сеть кофеен, 4 точки, Казань",
  "goal": "Привлечь аудиторию 18-30",
  "budget_rub_month": 150000,
  "horizon": "квартал"
}
```

## Expected output shape

- `MasterPlan.objective`: one strategic objective (performance promotion, geo-focused, KPI-anchored) — NOT a restatement of the request.
- `MasterPlan.domain_constraints`: RF channels only (VK Реклама, Telegram Ads, Яндекс Бизнес/Карты), realistic ~150k split, mandatory ad-marking (ОРД/erid), geo-radius focus, offline-conversion priority.
- `MasterPlan.success_criteria`: media plan with budget split, ≥3 creative concepts/channel, measurable KPIs (CPV/visit, reach, frequency, CR-to-visit), UTM + promo-code measurement.
- Final synthesis: one coherent quarterly strategy weaving media plan + analysis + content; numbers realistic for RF; activities marked.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (RF channels + marking + realistic budget) [0.25]
3. Measurability (KPIs + artifacts) [0.20]
4. RF-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: recommends Google/Meta Ads as a working channel, omits ad-marking, or fabricates KPI numbers.
