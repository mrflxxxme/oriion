---
id: 005
slug: content-plan-coauthors-rubric-split
difficulty: medium
primary_task: content-plan
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 005 — Content plan splitting rubrics across two co-authors

## Input

```json
{
  "task_type": "content-plan",
  "niche": "IT-карьера и собеседования",
  "channel_size": 34000,
  "current_cadence": "5 раз в неделю, 2 соавтора без чёткого распределения",
  "team_size": 2,
  "horizon": "месяц",
  "note": "соавторы дублируют темы и путаются, кто что готовит"
}
```

## Expected output shape

- `MasterPlan.objective`: fix rubric/topic overlap between two co-authors by
  assigning clear rubric ownership for a 34K IT-career channel.
- `MasterPlan.domain_constraints`: 5 posts/week is already above the solo
  sustainable default — acceptable only because it's a 2-person team, note
  this explicitly; channel above 10K — mention standing РКН/ad-marking
  applicability if any sponsored content occurs.
- `MasterPlan.success_criteria`: rubric skeleton where each rubric has ONE
  named owner + weekday, explicit anti-overlap rule (e.g. shared topic
  calendar).
- Final synthesis: coherent month plan with clear per-rubric ownership.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (ownership clarity + cadence-for-team-size reasoning) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: plan does not assign explicit per-rubric ownership at all.
