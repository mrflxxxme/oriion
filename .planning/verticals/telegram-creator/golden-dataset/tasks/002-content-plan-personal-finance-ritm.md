---
id: 002
slug: content-plan-personal-finance-ritm
difficulty: easy
primary_task: content-plan
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 002 — Content plan to fix an irregular posting rhythm

## Input

```json
{
  "task_type": "content-plan",
  "niche": "личные финансы",
  "channel_size": 8000,
  "current_cadence": "нерегулярно, 2-3 раза в неделю",
  "team_size": 1,
  "horizon": "месяц"
}
```

## Expected output shape

- `MasterPlan.objective`: turn an irregular posting habit into a sustainable
  rhythm for an 8K personal-finance channel, without burning out the solo
  author.
- `MasterPlan.domain_constraints`: channel size 8K is approaching the 10,000
  РКН blogger-registry threshold — flagged as an upcoming milestone, not yet
  mandatory; personal-finance niche → avoid specific investment
  guarantees/return-rate claims; rubrics pinned to weekdays for predictability.
- `MasterPlan.success_criteria`: monthly rubric skeleton (3-4 rubrics),
  2-week detailed plan, cadence realistic for solo author (not exceeding
  3-4 posts/week).
- Final synthesis: coherent plan; explicit note that 10K is close and what
  that will require once crossed.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (РКН-proximity flag + no investment guarantees) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: makes a specific investment-return promise, or fails to
  mention the approaching 10K РКН threshold at all.
