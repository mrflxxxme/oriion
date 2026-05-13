# Checklist: PR review (frontend)

Запускается перед эмиссией `tech.oriion.review.report.v1`. Все пункты `[x]` → verdict=`approved`, иначе → `revisions_requested`.

## Automated gates (must pass)

- [ ] **Lint clean.** `npm run lint` exit 0, no warnings.
- [ ] **Type-check clean.** `npm run typecheck` exit 0.
- [ ] **Tests green.** `npm test -- --run` exit 0; coverage не упало vs `<base>`.
- [ ] **Build succeeds.** `npm run build` exit 0.

## Tokens compliance

- [ ] **No inline colors.** Grep по diff: 0 matches на `#[0-9a-fA-F]{3,8}`, `rgb(`, `rgba(`, `hsl(` (исключая cssvars из tokens).
- [ ] **No raw spacing.** Все spacing классы — из Tailwind scale (`p-`, `m-`, `gap-`), не arbitrary `[14px]` без justification.
- [ ] **No raw typography.** Font-size/weight через tokens (`text-sm`, `font-medium`), не arbitrary values.

## Inventory conformance

- [ ] **All ui imports in inventory.** Каждый import из `frontend/src/components/ui/` найден в `_meta/ui/component-inventory.md`.
- [ ] **No ad-hoc components.** Новые компоненты вне inventory отсутствуют (либо явно proposed через designer handoff).

## Accessibility AA (WCAG 2.1)

- [ ] **Keyboard nav.** Все interactive elements достижимы Tab/Shift-Tab; focus visible.
- [ ] **ARIA semantics.** `role`, `aria-label`, `aria-describedby` корректны и не дублируют native semantic HTML.
- [ ] **Contrast AA.** Text/background contrast >= 4.5:1 (normal text), 3:1 (large text).
- [ ] **Focus management.** Modals/dialogs trap focus; close возвращает focus к trigger.

## Commit hygiene

- [ ] **Commit message format.** Каждый commit с `Phase:`, `Pipeline-role: frontend-implementer`, `Reviewers:`, `ADR-refs:` per [ADR-027 §4](../../../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md).
- [ ] **No `--amend`-style история.** Если revision — новый commit, не amend.
