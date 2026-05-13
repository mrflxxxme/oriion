# Checklist — a11y axe runbook (reviewer-frontend)

**Used by:** Workflow 2 — Accessibility WCAG 2.1 AA deep audit. Step-by-step playbook
для consistent a11y review execution.

---

## Pre-conditions

- [ ] Pre-flight setup done per `pr-review-frontend.md` (build / lint / typecheck / tests pass)
- [ ] Dev server running (`npm run dev`)
- [ ] Browser DevTools open
- [ ] axe DevTools extension installed (Chrome / Firefox)
- [ ] NVDA (Windows) или VoiceOver (macOS) available — для screen reader pass

---

## A. Automated scan (P0 — must run)

### A.1 axe DevTools (browser)

1. Navigate to route (e.g. `http://localhost:5173/auth/login`)
2. Open DevTools → "axe DevTools" tab
3. Click "Scan ALL of my page"
4. Review violations:
   - **Critical / Serious** → P0 blocker, log в findings
   - **Moderate / Minor** → P1 recommendation
5. Repeat for all routes touched by PR

### A.2 axe-cli (programmatic, CI-friendly)

```bash
# Single route
npx axe-cli http://localhost:5173/auth/login --tags wcag2a wcag2aa

# Multi-route (batch script — Wave 1+)
for route in auth/login auth/register cells/list cells/123/tasks/new; do
  npx axe-cli "http://localhost:5173/$route" --tags wcag2a wcag2aa --save "axe-$route.json"
done
```

### A.3 jest-axe (unit-test level)

- Verify component tests include `jest-axe` assertions:
  ```ts
  it('has no accessibility violations', async () => {
    const { container } = render(<LoginPage />);
    expect(await axe(container)).toHaveNoViolations();
  });
  ```
- Grep:
  ```bash
  grep -rnE "toHaveNoViolations" frontend/src --include="*.test.tsx"
  ```
  Components без a11y test → finding (REVIEW-CHECKLIST §J2).

---

## B. Keyboard navigation pass (P0 — manual)

For each interactive route:

1. **Focus initial element.** Click address bar, then Tab once — focus lands на first interactive element (skip-to-main or first focusable in main content).
2. **Tab through entire page.**
   - [ ] Tab order matches visual reading order (no tab-index jumps)
   - [ ] Every interactive element receives focus
   - [ ] Focus indicator visible на каждом element (`--shadow-focus-ring`)
   - [ ] No "focus trap leaks" outside modals
3. **Activate elements via keyboard:**
   - [ ] Enter / Space activate buttons
   - [ ] Enter activates links
   - [ ] Arrow keys navigate Tabs / RadioGroup / Combobox
   - [ ] Esc closes Dialog / Combobox / Popover
4. **Modal focus management** (if modal present):
   - [ ] Opening modal moves focus к first focusable в modal
   - [ ] Focus trapped within modal (Tab cycles inside)
   - [ ] Esc closes modal
   - [ ] Closing modal returns focus к invoking element

**Findings format:**
```
**C1** (keyboard nav): Tab order skips logout button at LoginPage.tsx:45 — element has `tabIndex={-1}` but should be focusable.
```

---

## C. Screen reader pass (P0 — manual)

### Setup
- **NVDA (Windows):** Free, https://www.nvaccess.org. Запустить, navigate к dev URL.
- **VoiceOver (macOS):** Cmd+F5 toggle. Use Ctrl+Option+Arrow keys для navigation.

### Per-route checklist

1. **Page title announced** when route loads (TanStack Router + `document.title` set per route)
2. **Headings hierarchy** — exactly one `<h1>` per page; nested `<h2>`/`<h3>` logical
3. **Landmarks** — main content в `<main>`, navigation в `<nav>`, complementary в `<aside>`
4. **Form labels** — каждый input announced с associated label text
5. **Form errors** — invalid input + `aria-describedby` → error text read out loud
6. **Button context** — icon-only buttons announced с `aria-label` (Russian)
7. **Live regions** — toasts announced при appearance (`role="status"` / `role="alert"`)
8. **Tables** — column headers announced при cell navigation
9. **Lists** — list count announced ("список из 5 элементов")
10. **State changes** — checkbox toggle, tab switch, etc. announced

**Findings format:**
```
**C6** (screen reader): Icon-only logout button at Header.tsx:23 has no `aria-label` — NVDA announces "button" with no context.
```

---

## D. Color contrast pass (P0 — DevTools)

### Method

1. Open DevTools → Elements tab → Select text element
2. Computed styles → Color → click swatch → DevTools shows contrast ratio
3. Verify per REVIEW-CHECKLIST §C10-§C13:
   - Body text (12-17px regular) ≥ 4.5:1
   - Large text (≥18px regular OR ≥14px bold) ≥ 3:1
   - Non-text UI (borders, focus rings, icons) ≥ 3:1

### Sample points per page

- [ ] Body text on `--bg-page` (`text-primary` on `bg-page`)
- [ ] Secondary text (`text-secondary` on `bg-page`)
- [ ] Muted text (`text-tertiary` on `bg-page`)
- [ ] Text on `bg-elevated` (cards)
- [ ] Link text in default state
- [ ] Focus ring contrast against adjacent surface
- [ ] Icon color against parent surface
- [ ] Both dark mode (default) AND light mode (toggle `[data-theme="light"]`)

**Findings format:**
```
**C12** (contrast): Border `--border-default` (#334155) on `--bg-elevated` (#1e293b) has contrast 1.6:1 — below 3:1 minimum. AppShell.tsx:34.
```

---

## E. Reduced motion pass (P0 — OS toggle)

### Setup
- **Windows:** Settings → Accessibility → Visual effects → Animation effects OFF
- **macOS:** System Settings → Accessibility → Display → Reduce motion ON

### Verification

1. Reload route after toggle
2. **Skeleton pulse animation** — disabled
3. **Modal slide-in transition** — replaced by opacity fade ≤150ms
4. **Toast slide-in** — replaced by opacity fade
5. **Hover transitions on buttons** — instant OR ≤150ms fade
6. **Page transitions** — instant OR ≤150ms

**Findings format:**
```
**C26** (reduced motion): Skeleton pulse continues despite `prefers-reduced-motion: reduce`. Skeleton.tsx:18 uses `animate-pulse` without conditional.
```

---

## F. Tooling notes (memory persist)

Patterns to log в `agent-memory:reviewer-frontend`:

- **Accepted false positives** — axe rules consistently flagged but project-accepted (document why)
- **Missing axe coverage** — axe-cli misses focus-trap leaks (use NVDA для manual confirmation)
- **Performance trade-offs** — heavy a11y tests slow CI; balance jest-axe per component vs Playwright a11y suite

---

## G. Verdict integration

A11y findings merged в Workflow 1 verdict:

- **Critical / Serious axe violation** OR **manual keyboard nav fail** OR **contrast <3:1** → P0 blocker → `request_changes`
- **Moderate axe violation** OR **screen reader minor announcement issue** → P1 recommendation (defer ОК cycle <3)
- **Acceptable per memory.md project pattern** → noted в revision doc "Accepted exceptions" section

---

## References

- `.claude/agents/reviewer-frontend/workflows.md` Workflow 2
- `_meta/ui/REVIEW-CHECKLIST.md` §C (27 a11y items)
- WCAG 2.1 AA — https://www.w3.org/WAI/WCAG21/quickref/
- axe DevTools — https://www.deque.com/axe/devtools/
- NVDA — https://www.nvaccess.org
- VoiceOver — https://www.apple.com/accessibility/vision/
