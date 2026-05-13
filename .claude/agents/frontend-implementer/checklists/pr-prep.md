# Checklist: PR-prep перед handoff к reviewers

Запускается перед эмиссией `tech.oriion.code.commit.v1`. Все пункты `[x]` — иначе handoff блокируется.

- [ ] **Lint clean.** `npm run lint` exit 0, без warning'ов.
- [ ] **Type-check clean.** `npm run typecheck` exit 0.
- [ ] **Tests pass.** `npm test -- --run` exit 0 (минимум новый код покрыт юнит-тестами).
- [ ] **Atomic commits.** Каждый commit — одно logical change (один файл / одна fix). Нет «WIP» или «misc» commits.
- [ ] **Commit message format.** Каждый commit использует Conventional Commits + `Phase:` + `Pipeline-role: frontend-implementer` + `Reviewers: ...` per [ADR-027 §4](../../../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md).
- [ ] **Tokens-only.** Grep по diff — нет inline `#hexcolors`, `rgb()`, raw px-values (всё через Tailwind classes / design-tokens).
- [ ] **Inventory match.** Все используемые компоненты есть в `_meta/ui/component-inventory.md`. Новых — нет (или явно flag'нуто в design handoff).
- [ ] **A11y baseline.** Mocks `a11y-must-have` отражены в коде: aria-labels, focus-management, keyboard handlers.
- [ ] **No secrets.** Diff не содержит API keys / passwords / `.env` mutations.
- [ ] **Push успешен.** `git push --force-with-lease origin <feature-branch>` exit 0.
