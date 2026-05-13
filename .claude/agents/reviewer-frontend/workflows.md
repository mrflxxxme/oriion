# Reviewer (frontend) — workflows

---

## Playbook 1: Review fresh commits from frontend-implementer

**Entry:** inbound `tech.oriion.code.commit.v1` (revision_iteration=0).

**Шаги:**

1. **Fetch context.** `git fetch && git checkout <branch>`. Load `tokens_used_map`, `components_used` из payload + diff `<base>..HEAD`.
2. **Run automated checks (parallel via Bash).**
   - `npm run lint` (ожидаем clean).
   - `npm run typecheck` (clean).
   - `npm test -- --run` (зелёные).
   - Grep по diff на `#[0-9a-f]{3,6}`, `rgb(`, raw `px` values вне tokens — должно быть 0 matches.
3. **Tokens compliance.** Каждый класс/value в diff'е cross-check'нуть с `_meta/ui/design-tokens.md`. Зафиксировать violations.
4. **Inventory conformance.** Каждый import из `frontend/src/components/ui/` cross-check'нуть с `_meta/ui/component-inventory.md`. Новые компоненты вне inventory — violation.
5. **Accessibility AA.** Spawn `Accessibility Auditor` skill для WCAG 2.1 AA checklist (keyboard-nav, contrast, focus-management, aria-attrs).
6. **Run `checklists/pr-review-frontend.md`.** Все пункты `[x]` → verdict=`approved`, иначе → `revisions_requested`.
7. **Compose handoff.** Если approved — `tech.oriion.review.report.v1` к verifier. Если revisions — write `revisions/<phase>-reviewer-frontend.md` + handoff обратно к frontend-implementer.

**Exit:** verdict эмитирован, findings персистированы в memory если pattern recurring.

---

## Playbook 2: Re-review after fix

**Entry:** inbound `tech.oriion.code.commit.v1` с `revision_iteration >= 1`.

**Шаги:**

1. **Focus diff.** Сравнить только новые commits (после предыдущего review).
2. **Verify ВСЕ предыдущие findings закрыты.** Cross-check с `revisions/<phase>-reviewer-frontend.md`.
3. **Re-run automated checks** (lint, typecheck, tests, grep).
4. **Spot-check no regression** в ранее approved областях.
5. **Emit verdict.** Если `revision_iteration == 3` и ещё есть violations — handoff к architect для эскалации к founder.

**Exit:** verdict эмитирован или эскалация.
