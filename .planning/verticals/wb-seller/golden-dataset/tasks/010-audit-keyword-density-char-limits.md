---
id: 010
slug: audit-keyword-density-char-limits
difficulty: medium
primary_task: audit
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (audit mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 010 — Audit keyword density + char limits (medium)

## Input

```json
{
  "task_type": "audit",
  "sku_context": { "artikul": "33445566", "category_hint": "Мужчинам > Одежда > Куртки" },
  "existing_listing": {
    "title": "Куртка мужская куртка зимняя куртка пуховая куртка теплая куртка стильная",
    "description": "Куртка мужская — лучшая куртка зимняя куртка для холодной зимы. Эта куртка пуховая теплая куртка стильная куртка. Купите куртку! [keyword 'куртка' x18 в description 800 chars]",
    "keywords": ["куртка", "куртка мужская", "куртка зимняя", "куртка пуховая", "куртка теплая", "куртка стильная", "куртка длинная", "куртка чёрная", "куртка"]
  },
  "audit_scope": ["keyword_stuffing", "char_limits", "duplicate_keywords"]
}
```

## Expected output shape

- `findings`: ≥ 3 entries
  - `keyword-stuffing` flag: «куртка» 18x в description (estimate density > 12% → penalized)
  - `duplicate-keyword` flag: «куртка» repeated в keywords array
  - `title-stuffing` flag: «куртка» 6x в title — readability + ranking-penalty risk
- `severity`: `warn` для всех (algorithm penalty risk, not hard block)
- `suggested_fixes`: rewritten content без stuffing, sustaining keyword diversity (синонимы: «пуховик», «парка»)

## Rubric

1. Factual accuracy [0.30] — корректный count keyword occurrences
2. WB-compliance [0.25] — корректная attribution к WB-ranking-algorithm penalty
3. Conversion-orientation [0.20] — fix добавляет synonym diversity
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: stuffing not detected ИЛИ fix содержит само stuffing
