---
id: 008
slug: audit-image-specs-only
difficulty: easy
primary_task: audit
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (audit mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 008 — Audit image specs compliance (easy)

## Input

```json
{
  "task_type": "audit",
  "sku_context": { "artikul": "11223344", "category_hint": "Электроника > Аудиотехника > Колонки портативные" },
  "existing_listing": {
    "images": [
      { "url": "...img1...", "width": 600, "height": 600, "format": "jpg", "size_kb": 320 },
      { "url": "...img2...", "width": 900, "height": 1200, "format": "jpg", "size_kb": 580 },
      { "url": "...img3...", "width": 400, "height": 400, "format": "png", "size_kb": 80 }
    ]
  },
  "audit_scope": ["image_specs"]
}
```

## Expected output shape

- `artifact.findings`: minimum 2 entries
  - `img1` flagged: 600x600 below WB-recommend 1200x1600
  - `img3` flagged: 400x400 значительно below minimum + PNG without alpha justification
- `severity`: `warn` для img1, `block` для img3 (below WB hard-minimum)
- `suggested_fix`: provide target resolution + format guidance

## Rubric

1. Factual accuracy [0.30] — correct WB image rules cited (с source_idx)
2. WB-compliance [0.25] — accurate severity tier
3. Conversion-orientation [0.20] — explain ranking-impact briefly
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: any of 3 images mislabeled severity
