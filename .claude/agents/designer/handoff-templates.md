# Designer — handoff templates

Все envelope-форматы валидируются по [`_shared/handoff-schema.json`](../_shared/handoff-schema.json) (CloudEvents 1.0 compatible).

---

## Inbound: `tech.oriion.plan.ui_phase.v1` (от planner)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.plan.ui_phase.v1",
  "source": "/oriion/agents/planner",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "phase-<phase-id>",
  "datacontenttype": "application/json",
  "data": {
    "phase_id": "00.7",
    "pipeline_template": "frontend-feature",
    "ui_spec": {
      "pages": [...],
      "components_used": [...],
      "new_components_needed": []
    },
    "tokens_version": "nordic-warm@1.0",
    "references": ["_meta/ui/design-tokens.md", "_meta/ui/component-inventory.md"]
  }
}
```

Designer обязан подтвердить receipt в `phase-state:<phase-id>` namespace или вернуть `tech.oriion.handoff.error.v1` если `ui_spec` отсутствует/невалиден.

---

## Outbound: `tech.oriion.design.mock.v1` (к frontend-implementer)

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
    "mocks": [
      {
        "page_slug": "cells-list",
        "preview_path": ".tmp/mocks/cells-list.html",
        "screenshot_path": "_meta/ui/reference-screens/cells-list.png",
        "tokens_used": ["color.primary", "spacing.lg", "..."],
        "components_used": ["Button", "Card", "Table", "EmptyState"]
      }
    ],
    "validation_report": {
      "all_states_covered": true,
      "all_components_in_inventory": true,
      "a11y_must_have_addressed": true,
      "new_components_needed": []
    },
    "checklist_passed": "checklists/mock-handoff.md"
  }
}
```

---

## Schema reference

Все типы событий должны быть зарегистрированы в `_shared/handoff-schema.json`. При расширении (новый payload-shape) — handoff к architect для review schema-evolution.
