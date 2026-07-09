---
id: 029
slug: monetization-subscription-vs-course-decision
difficulty: medium
primary_task: monetization-and-repurposing
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 029 — Paid-subscription tier vs. a full course product

## Input

```json
{
  "task_type": "monetization-and-repurposing",
  "niche": "иллюстрация и цифровой арт",
  "channel_size": 60000,
  "team_size": 2,
  "question": "запускать платную подписку в Stars на эксклюзивный контент или делать полноценный курс по иллюстрации?"
}
```

## Expected output shape

- `MasterPlan.objective`: help the author (60K channel, 2-person team, the
  "Курс-автор" persona half of this vertical per ADR-017) decide between a
  Stars paid-subscription tier and a full digital course product — or
  recommend sequencing both.
- `MasterPlan.domain_constraints`: a paid-subscription tier is lower-effort/
  lower-ceiling recurring income (Stars mechanics, per domain-brief §3.2); a
  full course is higher-effort, higher-ceiling, but requires more
  production time from a 2-person team; no specific revenue-figure
  guarantee for either path.
- `MasterPlan.success_criteria`: a comparative framework (effort vs. ceiling
  vs. team capacity) with a reasoned recommendation, not a flat "do both
  immediately" without sequencing.
- Final synthesis: clear recommendation + rationale + suggested sequencing.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct tradeoff framing for both models) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: presents a specific guaranteed revenue number for the course
  or subscription tier as fact.
