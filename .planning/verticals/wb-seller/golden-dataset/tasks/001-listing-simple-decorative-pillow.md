---
id: 001
slug: listing-simple-decorative-pillow
difficulty: easy
primary_task: listing-generation
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 001 — Generate listing для простой декоративной подушки

## Input

```json
{
  "task_type": "listing-generation",
  "sku_context": {
    "category_hint": "Дом и сад > Текстиль > Декоративные подушки",
    "product_name_user": "Подушка декоративная 40x40 хлопок",
    "key_features": ["размер 40x40", "100% хлопок", "съёмный чехол", "цвет беж"],
    "price_rub": 990
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `primary_variant.title`: ≤ 60 chars, includes core keywords («подушка декоративная», «40x40», «хлопок»)
- `primary_variant.description`: 1000-3000 chars, structured (материал → размер → характеристики → применение)
- `primary_variant.keywords`: 15-25 entries, no stuffing
- `primary_variant.char_counts` populated correctly
- `compliance_check.status`: `passed`
- `sources_used`: ≥ 2 indices referring к research_artifact

## Rubric (LLM-as-judge criteria)

1. Factual accuracy [weight 0.30] — все features из input присутствуют, ничего invented
2. WB-compliance [0.25] — char limits соблюдены, нет restricted words, нет markdown
3. Conversion-orientation [0.20] — keywords покрывают search-intent (размер + материал + категория)
4. Tone match [0.15] — professional-friendly без излишней formality
5. Format correctness [0.10] — valid JSON output, char_counts корректны

## Pass threshold

- Aggregate score ≥ 0.75
- Hard fail если: hallucinated feature (не из input) ИЛИ compliance_check.status = flagged
