---
id: 003
slug: content-plan-parenting-mixed-formats
difficulty: medium
primary_task: content-plan
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 003 — Mixed-format content plan for a parenting channel

## Input

```json
{
  "task_type": "content-plan",
  "niche": "родительство (дети 3-7 лет)",
  "channel_size": 22000,
  "current_cadence": "1 пост/день, читатели жалуются на однообразие",
  "team_size": 2,
  "horizon": "месяц",
  "note": "хотим разнообразить форматы — сторис, кружки, опросы"
}
```

## Expected output shape

- `MasterPlan.objective`: diversify format mix for a 22K parenting channel
  (currently text-only daily) to fight reader fatigue, while keeping the
  existing cadence.
- `MasterPlan.domain_constraints`: channel already above 10K — РКН
  blogger-registry compliance assumed already handled (ask to confirm, don't
  assume unregistered); team of 2 → can split rubric ownership; parenting
  niche → no unverified medical/developmental claims about children.
- `MasterPlan.success_criteria`: rubric skeleton mixing post/story/round-video/poll
  formats, each rubric assigned a weekday + team-member owner.
- Final synthesis: one coherent plan, explicit format rotation, team
  ownership split.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (format diversity + no medical claims) [0.25]
3. Measurability (rubric-to-format-to-owner mapping) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: makes an unverified child-development/medical claim, or
  ignores the 2-person team shape entirely.
