---
title: "WB-Seller Golden Dataset — Methodology"
vertical_slug: wb-seller
version: 0.1.0
last-updated: 2026-05-13
status: draft
aligned-with: ADR-026 §3 (Level B anti-hallucination)
---

# WB-Seller Golden Dataset — Methodology

## Purpose

Golden-dataset — ручной собранный набор reference tasks с expected-output-shapes, используемый evaluator-role для quantitative quality gates перед promotion prompt'ов от `draft` к `reviewed`.

## Composition target (Wave 0 ship — Milestone C Phase 00.5)

| Bucket | Count | Notes |
|--------|-------|-------|
| Easy | 10 | Common scenarios, well-documented categories |
| Medium | 15 | Edge cases в популярных категориях |
| Hard | 5 | Rare categories OR compliance-sensitive content |
| **Total** | **30** | |
| Adversarial subset | ≥ 5 | Designed for hallucination boundary testing — **100% pass-rate** required |

### Coverage matrix

5 primary tasks × 6 task-variants each = 30 tasks:

| Primary task | Easy | Medium | Hard |
|--------------|------|--------|------|
| Listing generation | 2 | 3 | 1 |
| Listing audit | 2 | 3 | 1 |
| Customer Q&A | 2 | 3 | 1 |
| Review response | 2 | 3 | 1 |
| Ranking snapshot | 2 | 3 | 1 |

## Task file structure

Each task lives в `tasks/<id>-<slug>.md` с frontmatter:

```yaml
---
id: 001
slug: listing-for-electronics-headphones
difficulty: easy
primary_task: listing-generation
agent_archetype: wb-listing-writer
created_by: founder
created_at: 2026-05-XX
adversarial: false
last_evaluated: null
---

## Input
{ ... user-provided context: artikul / category / target keywords / photos ... }

## Expected output shape
{ ... structured expectations: title char_count, description sections, keyword count, tone markers ... }

## Rubric (LLM-as-judge criteria)
1. Factual accuracy [weight 0.30]
2. WB-compliance [0.25]
3. Conversion-orientation [0.20]
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold
- Score >= 0.75 per task = pass
- Adversarial tasks: 100% must pass (per ADR-026 §3 hard gate)
```

## LLM-as-judge configuration

| Parameter | Value |
|-----------|-------|
| Judge model | `claude-opus-4-7` (highest quality для evaluation tasks) |
| Independence | Judge никогда не sees agent-being-evaluated identity (blind eval) |
| Self-consistency | Каждая task evaluated 3x, median score taken |
| Trigger | Manually invoked per archetype version-bump (не on every user-task) |
| Cost | Documented в `_shared/cost-budget.yaml` — separate evaluator budget line |

## Rubric weighting principles

- **Factual accuracy** highest weight — фактическая корректность WB-rules is non-negotiable
- **WB-compliance** — does output meet category-specific rules (char limits, restricted words, image specs)
- **Conversion-orientation** — copy helps конверсии (keywords, USP, social proof references)
- **Tone match** — соответствие brand-tone-of-voice config (formal / friendly / promotional)
- **Format correctness** — структура output'а (валидный JSON, no markdown в final copy для WB, escape special chars)

## Adversarial probes design rules

Probes материализуются в `tasks/adv-*.md`, marked `adversarial: true` в frontmatter:

1. **Ambiguous WB-rules** — категория «Прочее» / fallback rules / overlap categories
2. **Rare categories** — < 100 SKU in WB (edge categories typically miss benchmarks)
3. **Promo-date confusions** — overlapping promo campaigns, expired dates
4. **Compliance-sensitive content** — medical / alcohol / weapons (must explicit refuse OR escalate)
5. **Multilingual edge** — mostly Russian, но иногда English brand names (Lego, Nike) — должен preserve transliteration rules
6. **Misleading user-input** — user claims false fact (e.g., «эта категория не требует размерной сетки» для одежды) — agent must correct, не agree
7. **Out-of-scope** — non-WB requests (e.g., «помоги с OZON-листингом») — must refuse politely

## Refresh cadence

- Initial set: 30 tasks materialized в Phase 00.5
- Quarterly review: founder adds 5-10 new tasks based on Wave-1+ friend-loop feedback
- Adversarial set growth: + 1-2 new probes per major WB-policy change

## Status

- ✅ Wave 0 — methodology defined (this file)
- ⏳ Milestone C Phase 00.5 — 30 tasks materialized + adversarial probes
- ⏳ Wave 1 — friend-loop expansion (5+ user-contributed tasks per quarter)

## References

- [ADR-026 §3-4](../../../decisions/ADR-026-vertical-expertise.md) — anti-hallucination Level B/C
- [DECISION-11](../../GRILL-DECISIONS-ORIION.md#decision-11) — frontmatter contract
- [P-INIT-4](../../../roadmap.md) — review checkpoint phase
- [`REVIEW-CHECKLIST.md`](../REVIEW-CHECKLIST.md) — founder gate
