# `verticals/wb-seller/golden-dataset/tasks/` — Golden-task corpus

> 30 materialized golden tasks covering the WB-Seller core competencies.
> Tasks pair an `input` (user request) with an `expected_output` (ideal
> answer + acceptance criteria) so the `evaluator` AI role (per
> [ADR-023](../../../../decisions/ADR-023-ai-team-runtime.md)) can score
> any prompt change deterministically.

## Coverage matrix

5 primary task-types × 6 variants each = 30 tasks total:

| Task type | Files | Captures |
|---|---|---|
| `001-listing-*` | 001-005 | Listing card optimization (title, bullets, images, infographics) |
| `006-keyword-*` | 006-010 | Keyword research + clustering for WB search |
| `011-ranking-*` | 011-015 | Position-tracking + ranking-improvement playbooks |
| `016-ads-*` | 016-020 | WB Ads campaign setup + scaling + A/B testing |
| `021-analytics-*` | 021-025 | Sales analytics + commission reconciliation + return-rate analysis |
| `026-ranking-*` | 026-030 | Advanced ranking strategies (seasonality, competitor displacement) |

## Frontmatter contract

Each task file uses YAML frontmatter:

```yaml
---
id: 003-listing-bullet-optimization
type: listing
difficulty: medium
expected_tools: [wb_specialist, analyst]
acceptance_criteria:
  - title_optimized: true
  - bullets_count: 5
  - includes_keywords: [<top-5>]
  - ru_compliant: true
---
```

See [ADR-026](../../../../decisions/ADR-026-vertical-expertise-pipeline.md) §3 for the full frontmatter schema.

## Evaluator pass rate

Per [ADR-026](../../../../decisions/ADR-026-vertical-expertise-pipeline.md) §5 — Wave-acceptance gate requires **≥ 90 % pass rate** on the golden corpus. Below 90 % blocks the vertical's Wave-N-to-N+1 gate.
