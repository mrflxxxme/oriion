---
id: 026
slug: repurpose-long-post-into-teaser-followup
difficulty: easy
primary_task: monetization-and-repurposing
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 026 — Repurpose one long post into a story teaser + short follow-up

## Input

```json
{
  "task_type": "monetization-and-repurposing",
  "niche": "садоводство",
  "original_post": "Длинный пост (1200 знаков) про 5 ошибок при посадке томатов рассадой, с подробным разбором каждой ошибки.",
  "goal": "получить больше охвата из уже готового материала, не переписывая с нуля"
}
```

## Expected output shape

- `MasterPlan.objective`: repurpose the existing 1,200-character post into a
  story teaser + a short standalone follow-up, extracting the material
  rather than rewriting it from scratch.
- `MasterPlan.domain_constraints`: the teaser should tease ONE of the 5
  mistakes (not all 5, to keep it story-length), the follow-up should
  reference back to the original longer post for full detail rather than
  duplicating all 1,200 characters of content.
- `MasterPlan.success_criteria`: a story-text artifact + a short follow-up
  artifact, both clearly derived from the original without inventing new
  claims about tomato-planting not in the source.
- Final synthesis: both pieces + a one-line publish-sequence note.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (repurposing technique, not verbatim duplication) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: invents new gardening claims not present in the original
  post, or simply reposts the full 1,200 characters as the "teaser."
