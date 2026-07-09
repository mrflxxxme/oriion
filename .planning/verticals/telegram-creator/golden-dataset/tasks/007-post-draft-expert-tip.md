---
id: 007
slug: post-draft-expert-tip
difficulty: easy
primary_task: post-drafting
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 007 — Draft an expert-take post

## Input

```json
{
  "task_type": "post-drafting",
  "niche": "продуктивность",
  "rubric": "экспертный понедельник",
  "topic": "почему списки дел на день обычно не работают",
  "tone": "уверенный, без канцелярита"
}
```

## Expected output shape

- `MasterPlan.objective`: produce one platform-native expert-take post on the
  given topic for the "экспертный понедельник" rubric.
- `MasterPlan.domain_constraints`: Telegram-native formatting (short
  paragraphs, no markdown artifacts, appropriate emoji use per
  domain-brief), tone = confident/no corporate jargon, no unverifiable
  productivity-guarantee claims ("this will 10x your output").
- `MasterPlan.success_criteria`: one ready-to-publish draft, plain Telegram
  formatting, length appropriate for a short expert-take post.
- Final synthesis: the drafted post text, ready for manual publish (no
  autonomous send).

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (Telegram-native formatting) [0.25]
3. Measurability (concrete, ready-to-publish draft) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: output contains markdown syntax that doesn't render in
  Telegram (e.g. raw `**bold**`/`##` headers) presented as final copy.
