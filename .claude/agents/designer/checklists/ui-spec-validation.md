# Checklist — ui-spec validation (designer)

**Used by:** Workflow 1 step 2 — perform before ui-ux-pro-max invocation. Block invocation if any P0 item fails.

---

## Pre-flight (P0 — blocks invocation)

- [ ] **PF1.** Phase-spec.md exists и readable
- [ ] **PF2.** `ui-spec:` block present и non-empty
- [ ] **PF3.** `pages[]` array non-empty (минимум 1 page)
- [ ] **PF4.** `_meta/ui/design-tokens.md` Read и в context window
- [ ] **PF5.** `_meta/ui/component-inventory.md` Read и в context window
- [ ] **PF6.** `_meta/ui/UI-DESIGN-PLAYBOOK.md` Read и в context window
- [ ] **PF7.** `_meta/ui/REVIEW-CHECKLIST.md` Read и в context window

---

## A. Per-page structural coverage (P0)

For **each** `pages[N]` entry в ui-spec:

- [ ] **A1.** `slug` set (kebab-case route identifier)
- [ ] **A2.** `layout` specified (one of: dashboard / auth-shell / detail / fullscreen / drawer)
- [ ] **A3.** `content-slots` non-empty (minimum: header + main, or layout-specific equivalent)
- [ ] **A4.** `content-slots` describes information architecture clearly (not just "form" — what fields, what flow)
- [ ] **A5.** `interaction-states` array enumerated explicitly
- [ ] **A6.** State coverage: `loading` present (если data-driven)
- [ ] **A7.** State coverage: `empty` present (если list/feed surface)
- [ ] **A8.** State coverage: `error` present (если data-driven OR mutating)
- [ ] **A9.** State coverage: `populated` present (always — base default)
- [ ] **A10.** State coverage: `streaming` present (если SSE/WebSocket surface, e.g. task-result)

---

## B. Accessibility coverage (P0)

- [ ] **B1.** `a11y-must-have` array non-empty per page
- [ ] **B2.** `keyboard-nav` listed (always required — minimum)
- [ ] **B3.** `screen-reader-labels` listed (always required)
- [ ] **B4.** `focus-trap` listed если page содержит modal или drawer
- [ ] **B5.** `reduced-motion` listed если page содержит non-essential transitions
- [ ] **B6.** `aria-live` listed если page имеет dynamic content updates (toasts / streaming / status messages)

---

## C. Component inventory compliance (P0)

- [ ] **C1.** `components-used` array non-empty per page
- [ ] **C2.** **Each** entry в `components-used` существует в `_meta/ui/component-inventory.md` (lookup name + match case)
- [ ] **C3.** Compound components use dot-notation reference (e.g. `Card.Header` not bare `CardHeader`)
- [ ] **C4.** `new-components-needed` is empty array OR each entry has:
   - `name` (PascalCase)
   - `purpose` (1 sentence)
   - `justification` (why none of 18 existing components compose)
   - `proposed props`
   - `states`
   - `a11y requirements`

---

## D. Cross-page consistency (P0 если phase touches multi-page surface)

- [ ] **D1.** Shared layout primitive used consistently (e.g. all auth pages share `AuthShell`)
- [ ] **D2.** Navigation pattern consistent (breadcrumb / tabs / sidebar — one pattern per layout type)
- [ ] **D3.** Empty/error copy уважает наследование (parent surface "Создайте..." vs child "Нет данных" rejected per anti-pattern)
- [ ] **D4.** Form patterns consistent (same validation copy style, same submit-button states)

---

## E. Outcomes (verdict)

After completing checklist:

### ✅ Proceed to ui-ux-pro-max invocation
- All P0 items passed
- Можно invoke ui-ux-pro-max per Workflow 1 step 4

### 🔄 Block invocation — ui-spec gap
- ≥1 P0 item failed
- Compose ONE focused clarifying question к planner OR founder
- Emit `tech.oriion.ui_spec.gap.v1` с specific gap reference (e.g. "pages[0].interaction-states missing `error` state per A8")
- Wait for planner response, re-run checklist

### 🚨 Escalate к architect
- Inventory gap (C4): new-components-needed без justification OR требует inventory contract change
- Cross-page inconsistency (D1-D4) на Wave-level invariant (cannot resolve в single phase)
- Emit `tech.oriion.conflict.escalation.v1` с context bundle

---

## Quick reference

```bash
# Verify ui-spec syntax (если YAML parser available)
yq '.ui-spec' .planning/roadmap/wave-0-foundation/phases/<phase>.md

# Verify components-used ⊆ inventory
grep "^### " .planning/_meta/ui/component-inventory.md | awk -F'. ' '{print $2}' > /tmp/inventory.txt
# затем compare с ui-spec extract
```

---

## References

- `.claude/agents/designer/workflows.md` Workflow 1
- `.planning/_meta/ui/UI-DESIGN-PLAYBOOK.md` §3.3 (pre-invocation context bundle)
- `.planning/_meta/ui/component-inventory.md` (truth для C2)
- `.planning/_meta/ui/REVIEW-CHECKLIST.md` (downstream gate)
