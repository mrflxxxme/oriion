---
id: 009
slug: post-draft-trending-topic-reaction
difficulty: medium
primary_task: post-drafting
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 009 — Draft a reaction post to a trending niche topic

## Input

```json
{
  "task_type": "post-drafting",
  "niche": "разработка ПО / карьера в IT",
  "rubric": "реакция на тренд",
  "trend_context": "в нише активно обсуждают, стоит ли джуну идти в AI-инструменты вместо изучения основ",
  "channel_size": 28000
}
```

## Expected output shape

- `MasterPlan.objective`: produce a reaction post giving the author's
  (well-reasoned, non-generic) take on the trending debate, feeding on
  Researcher-gathered context about the actual debate.
- `MasterPlan.domain_constraints`: reaction should reference the trend
  accurately (not invent positions no one holds), stay balanced/credible for
  an IT-career audience, avoid absolute claims ("AI tools are useless"/
  "never learn fundamentals") without nuance.
- `MasterPlan.success_criteria`: draft that engages with the real trend,
  offers a clear author POV, invites discussion (question/poll optional).
- Final synthesis: ready-to-publish reaction post.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (accurate trend framing, nuanced POV) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: misrepresents the trend context or takes an absolutist,
  unsupported stance presented as fact.
