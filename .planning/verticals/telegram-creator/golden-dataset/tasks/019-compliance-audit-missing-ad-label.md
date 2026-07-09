---
id: 019
slug: compliance-audit-missing-ad-label
difficulty: easy
primary_task: compliance-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 019 — Compliance audit: sponsored post missing the ad label

## Input

```json
{
  "task_type": "compliance-audit",
  "post_text": "Друзья, нашла крутой сервис доставки готовой еды — заказываю уже месяц, реально экономит время. Промокод CREATOR10 на первый заказ!",
  "is_sponsored": true,
  "advertiser": "ООО ЕдаСервис"
}
```

## Expected output shape

- `MasterPlan.objective`: audit this sponsored post for ФЗ-38 ad-marking
  compliance.
- `MasterPlan.domain_constraints`: the post text contains NO «Реклама» label,
  no advertiser name/INN, no erid token — all three are mandatory for a
  paid post regardless of how organic the tone reads.
- `MasterPlan.success_criteria`: a line-by-line risk/ok review flagging the
  missing label + missing advertiser data + missing erid, plus a
  compliant rewrite suggestion (label added, advertiser named, erid
  placeholder).
- Final synthesis: clear flags + concrete fix, not a vague "consider adding
  disclosure."

## Rubric (LLM-as-judge)

1. Strategic framing (correctly scoped as audit) [0.30]
2. Domain expertise (ФЗ-38 + marking specifics) [0.25]
3. Measurability (concrete flags + rewrite) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: misses that the post is unmarked despite `is_sponsored: true`
  being given explicitly.
