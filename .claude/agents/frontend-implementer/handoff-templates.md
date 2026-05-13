# Frontend implementer — handoff templates

Все envelope-форматы валидируются по [`_shared/handoff-schema.json`](../_shared/handoff-schema.json) (CloudEvents 1.0 compatible).

---

## Inbound: `tech.oriion.design.mock.v1` (от designer)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.design.mock.v1",
  "source": "/oriion/agents/designer",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "phase-<phase-id>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.7",
    "mocks": [...],
    "validation_report": {...},
    "checklist_passed": "checklists/mock-handoff.md"
  }
}
```

Frontend-implementer должен подтвердить `validation_report.all_components_in_inventory=true` и `a11y_must_have_addressed=true` перед началом implementation; иначе вернуть `tech.oriion.handoff.error.v1` к designer.

---

## Outbound: `tech.oriion.code.commit.v1` (к reviewer-frontend + reviewer-security)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.code.commit.v1",
  "source": "/oriion/agents/frontend-implementer",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "phase-<phase-id>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.7",
    "branch": "feature/wave-0-phase-00.7-frontend-skeleton",
    "commits": [
      {
        "sha": "abc1234",
        "message": "feat(ui): add CellsList route skeleton",
        "files_changed": ["frontend/src/routes/cells/index.tsx"],
        "pipeline_role": "frontend-implementer"
      }
    ],
    "tokens_used_map": {"color.primary": 4, "spacing.lg": 12},
    "components_used": ["Button", "Card", "Table"],
    "test_coverage": {"unit": 0.82, "integration": 0.65},
    "checklist_passed": "checklists/pr-prep.md",
    "revision_iteration": 0
  }
}
```

---

## Schema reference

Расширения формата — через handoff к architect для review schema-evolution в `_shared/handoff-schema.json`.
