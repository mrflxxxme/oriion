---
id: 001
slug: content-plan-new-cooking-channel
difficulty: easy
primary_task: content-plan
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 001 — Content plan for a brand-new cooking channel

## Input

```json
{
  "task_type": "content-plan",
  "niche": "домашняя кулинария (простые рецепты после работы)",
  "channel_size": 0,
  "current_cadence": "канал ещё не создан",
  "team_size": 1,
  "horizon": "месяц"
}
```

## Expected output shape

- `MasterPlan.objective`: one strategic objective — build a sustainable rubric
  skeleton + 2-week detailed plan for a brand-new solo cooking channel, not a
  vague "make good content" restatement.
- `MasterPlan.domain_constraints`: solo-author realistic cadence (~3-4
  posts/week per domain-brief §2, not daily from day one), 3-4 recurring
  rubrics pinned to weekdays, channel size 0 → no РКН/ad-marking constraints
  yet (explicitly note as not-yet-applicable, not omit silently).
- `MasterPlan.success_criteria`: monthly rubric skeleton + detailed 2-week
  plan, each rubric has a clear format (post/story/round-video).
- Final synthesis: one coherent content-plan document, rubrics + example
  topics per rubric, realistic solo-author cadence.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (realistic solo cadence + rubrication) [0.25]
3. Measurability (concrete rubric skeleton + 2-week plan) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: proposes daily posting for a solo new author without
  flagging burnout risk, or applies algorithmic-feed-gaming advice.
