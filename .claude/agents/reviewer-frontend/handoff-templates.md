# Reviewer (frontend) — handoff templates

Все envelope-форматы валидируются по [`_shared/handoff-schema.json`](../_shared/handoff-schema.json) (CloudEvents 1.0 compatible).

---

## Inbound: `tech.oriion.code.commit.v1` (от frontend-implementer)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.code.commit.v1",
  "source": "/oriion/agents/frontend-implementer",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "phase-<phase-id>",
  "data": {
    "phase_id": "00.7",
    "branch": "feature/wave-0-phase-00.7-frontend-skeleton",
    "commits": [...],
    "tokens_used_map": {...},
    "components_used": [...],
    "test_coverage": {...},
    "revision_iteration": 0
  }
}
```

---

## Outbound: `tech.oriion.review.report.v1` (к verifier или обратно к implementer)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.review.report.v1",
  "source": "/oriion/agents/reviewer-frontend",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "phase-<phase-id>",
  "data": {
    "phase_id": "00.7",
    "reviewer": "reviewer-frontend",
    "verdict": "approved | revisions_requested | escalated",
    "revision_iteration": 0,
    "findings": [
      {
        "severity": "blocker | major | minor",
        "file": "frontend/src/routes/cells/index.tsx",
        "line": 42,
        "expected": "Use design-token color.primary (amber-500)",
        "actual": "Inline hex #ff9800",
        "rule": "tokens-compliance"
      }
    ],
    "checklist_run": "checklists/pr-review-frontend.md",
    "next_role": "verifier | frontend-implementer | architect"
  }
}
```

Если `verdict=revisions_requested` — параллельно write `revisions/<phase>-reviewer-frontend.md` с тем же `findings[]` (Markdown table).

Если `verdict=escalated` (revision_iteration >= 3 и всё ещё violations) — `next_role=architect`, architect готовит context summary для founder.

---

## Schema reference

Изменения формата — через handoff к architect для review schema-evolution в `_shared/handoff-schema.json`.
