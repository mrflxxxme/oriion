---
id: 010
slug: post-draft-story-teaser-followup-pair
difficulty: medium
primary_task: post-drafting
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 010 — Draft a story-teaser + follow-up post pair

## Input

```json
{
  "task_type": "post-drafting",
  "niche": "путешествия бюджетно",
  "rubric": "анонс + разбор",
  "topic": "как я слетал в Стамбул за 15 тысяч рублей туда-обратно",
  "formats_requested": ["story-text", "follow-up post"]
}
```

## Expected output shape

- `MasterPlan.objective`: produce a two-part content pair — a short story
  teaser and a longer follow-up post — from one underlying trip story,
  demonstrating repurposing (per domain-brief §2/§4).
- `MasterPlan.domain_constraints`: story-text must be teaser-length (not a
  full retelling), follow-up must deliver on the teaser's promise; price
  figure (15,000 ₽) used consistently across both, not altered/inflated.
- `MasterPlan.success_criteria`: both a `story-text` and a `post`
  (follow-up) artifact, cross-referencing each other, consistent facts.
- Final synthesis: both drafts presented together with a clear
  teaser→follow-up publish sequence recommendation.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (teaser vs follow-up structure, repurposing) [0.25]
3. Measurability (two distinct linked artifacts) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: the two pieces are identical/near-duplicate text, or the
  price figure is inconsistent between them.
