# Evaluator — handoff templates

Все envelope-форматы валидируются по [`_shared/handoff-schema.json`](../_shared/handoff-schema.json) (CloudEvents 1.0 compatible).

---

## Inbound: `tech.oriion.prompt.candidate.v1` (от vertical-prompt-author)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.prompt.candidate.v1",
  "source": "/oriion/agents/vertical-prompt-author",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "vertical-<slug>-role-<role>",
  "data": {
    "vertical_slug": "wb-seller",
    "role": "coordinator",
    "prompt_path": "_meta/verticals/wb-seller/prompts/coordinator.md",
    "version": "0.2.0",
    "previous_version": "0.1.0",
    "frontmatter": {
      "verified_sources": [...],
      "status": "draft"
    },
    "golden_dataset_ref": "_meta/verticals/wb-seller/golden-dataset/",
    "adversarial_dataset_ref": "_meta/verticals/wb-seller/golden-dataset/adversarial/"
  }
}
```

---

## Outbound: `tech.oriion.evaluator.verdict.v1` (к founder-queue или vertical-prompt-author)

```json
{
  "specversion": "1.0",
  "type": "tech.oriion.evaluator.verdict.v1",
  "source": "/oriion/agents/evaluator",
  "id": "<uuid>",
  "time": "<iso8601>",
  "subject": "vertical-<slug>-role-<role>",
  "data": {
    "vertical_slug": "wb-seller",
    "role": "coordinator",
    "prompt_version": "0.2.0",
    "verdict": "promote_recommended | rework_required | invalid_frontmatter",
    "metrics": {
      "golden_pass_rate": 0.83,
      "golden_total": 30,
      "golden_passed": 25,
      "adversarial_pass_rate": 1.0,
      "adversarial_total": 5,
      "adversarial_passed": 5
    },
    "per_task_breakdown": [
      {
        "task_id": "001-...",
        "difficulty": "easy",
        "passed": true,
        "rubric_score": 0.9,
        "reasoning": "Output covers all expected fields..."
      }
    ],
    "divergence_flags": [],
    "next_role": "founder | vertical-prompt-author",
    "checklist_passed": "checklists/golden-dataset-run.md"
  }
}
```

**Invariant:** если `adversarial_pass_rate < 1.0` → `verdict != promote_recommended` (must be `rework_required`).

---

## Schema reference

Расширения формата — через handoff к architect для schema-evolution в `_shared/handoff-schema.json`.
