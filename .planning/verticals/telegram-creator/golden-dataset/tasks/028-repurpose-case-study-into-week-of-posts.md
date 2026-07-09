---
id: 028
slug: repurpose-case-study-into-week-of-posts
difficulty: medium
primary_task: monetization-and-repurposing
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 028 — Repurpose a multi-part case study into a week's worth of posts

## Input

```json
{
  "task_type": "monetization-and-repurposing",
  "niche": "консалтинг для малого бизнеса",
  "source_material": "подробный кейс на 4 части: диагностика проблемы клиента, решение, внедрение, результат (общий объём — большой лонгрид)",
  "cadence_target": "5 постов на неделю"
}
```

## Expected output shape

- `MasterPlan.objective`: decompose one long-form 4-part case study into a
  week's worth (5 posts) of standalone-readable content, without losing the
  narrative arc.
- `MasterPlan.domain_constraints`: each post should be self-contained enough
  to make sense to a reader who missed a prior day, while still building
  toward the case study's conclusion (cliffhanger/continuation structure);
  no invented client details beyond what the source case study states; if a
  quantified result is mentioned, it must come from the source, not be
  embellished.
- `MasterPlan.success_criteria`: a 5-post breakdown mapping to the
  diagnosis/solution/implementation/result arc (with one extra post — e.g.
  a wrap-up/lessons-learned), each post format-appropriate for daily
  Telegram consumption.
- Final synthesis: the 5-post plan/drafts, consistent facts across all 5.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (narrative decomposition, fact consistency) [0.25]
3. Measurability (5 concrete linked posts) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: invents a client result/number not present in the source
  case study, or the 5 posts contradict each other on the facts.
