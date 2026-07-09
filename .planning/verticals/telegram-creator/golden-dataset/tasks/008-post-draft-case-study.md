---
id: 008
slug: post-draft-case-study
difficulty: easy
primary_task: post-drafting
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 008 — Draft a case-study post

## Input

```json
{
  "task_type": "post-drafting",
  "niche": "маркетинг для малого бизнеса",
  "rubric": "кейс среды",
  "case_facts": "клиент — локальная кофейня, за 2 месяца таргета в VK выросли заявки на кейтеринг на 40%",
  "tone": "конкретика, без воды"
}
```

## Expected output shape

- `MasterPlan.objective`: produce a case-study post using ONLY the supplied
  facts, no invented numbers beyond the given "40% growth over 2 months."
- `MasterPlan.domain_constraints`: no fabricated additional metrics, no
  guarantee that the same result applies to the reader's business, RU
  channel (VK) referenced accurately.
- `MasterPlan.success_criteria`: draft with a clear before/after structure
  using exactly the given facts.
- Final synthesis: ready-to-publish case-study draft.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (fact-fidelity, no embellishment) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: invents additional metrics/numbers not present in
  `case_facts`, or implies a guaranteed result for the reader.
