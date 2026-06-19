---
id: 007
slug: compliance-audit-vk-ad-copy
difficulty: medium
primary_task: compliance-audit
agent_archetype: master-agency-marketing-ru
archetype_path: master → coordinator → researcher/analyst
created_by: ai-baseline
created_at: 2026-06-19
adversarial: false
last_evaluated: null
---

# Task 007 — Compliance audit of VK ad copy (ФЗ-38 + marking)

## Input

```json
{
  "task_type": "compliance-audit",
  "channel": "VK",
  "ad_copy": "Лучший кофе в Казани! Дешевле всех конкурентов. Закажи сейчас.",
  "advertiser": "ООО Ромашка"
}
```

## Expected output shape

- `MasterPlan.objective`: a compliance-audit objective (ФЗ-38 + marking), not a new campaign.
- `MasterPlan.domain_constraints`: ФЗ-38 (unsubstantiated superlatives «лучший»/«дешевле всех» are violations), mandatory erid + «реклама» label + advertiser data, VK moderation specifics.
- `MasterPlan.success_criteria`: line-by-line risk/ok review, concrete rewrites, marking checklist.
- Final synthesis: flags «Лучший» and «Дешевле всех конкурентов» as ФЗ-38 risks with compliant rewrites + a marking checklist.

## Rubric (LLM-as-judge)

1. Strategic framing (correctly scoped as audit) [0.30]
2. Domain expertise (ФЗ-38 + marking specifics) [0.25]
3. Measurability (actionable per-line verdicts + checklist) [0.20]
4. RF-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: misses the superlative violation OR omits the marking requirement.
