# ui/ — UI Design System

Артефакты UI-системы: component inventory, design tokens, design playbook, review-checklist. UI-spec'ы по фазам добавляются здесь же.

**ADR refs:** [ADR-016](../decisions/ADR-016-team-first-ux.md) (team-first UX), [ADR-021](../decisions/ADR-021-ai-generated-pixel-pipeline.md) (AI-generated pixel)

## Файлы

| Файл | Содержание |
|---|---|
| [`component-inventory.md`](./component-inventory.md) | Список 18 компонентов под материализацию в Phase 00.7 |
| [`design-tokens.md`](./design-tokens.md) | Цвета, типографика, spacing, shadows |
| [`UI-DESIGN-PLAYBOOK.md`](./UI-DESIGN-PLAYBOOK.md) | Принципы UX, патерны, наследие Teamly |
| [`REVIEW-CHECKLIST.md`](./REVIEW-CHECKLIST.md) | Дизайн-review checklist (accessibility, consistency, brand) |

## Когда читать

- В начале frontend phase — `component-inventory.md` + `design-tokens.md`.
- При создании нового экрана — `UI-DESIGN-PLAYBOOK.md` для принципов.
- Перед PR review — `REVIEW-CHECKLIST.md`.

## Расширение

UI-spec'ы по конкретным фазам добавляются в эту же папку с именем `UI-SPEC-<phase>.md` (через `gsd:ui-phase` в момент входа в фазу).
