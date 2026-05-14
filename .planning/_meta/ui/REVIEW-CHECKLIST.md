# Frontend Review Checklist

- **Version:** 0.1.0
- **Audience:** `reviewer-frontend` role
- **Scope:** Wave 0 frontend PRs consuming `_meta/ui/design-tokens.md` + `_meta/ui/component-inventory.md`
- **Verdict format:** per ADR-027 — `approve` / `request_changes` / `escalate`. Max 3 revision cycles.

> This checklist is the enforcement layer for tokens + inventory + accessibility. Reviewer MUST run through every P0 item. P1 items recommended; can be deferred to follow-up phase with explicit `revisions/<phase>-reviewer-frontend.md` note.

---

## Pre-review setup (mandatory)

- [ ] Read phase-spec `ui-spec:` block (understand intent)
- [ ] Read `_meta/ui/design-tokens.md` (token vocabulary)
- [ ] Read `_meta/ui/component-inventory.md` (allowed components)
- [ ] Pull PR branch locally: `git fetch origin <branch> && git checkout <branch>`
- [ ] Install deps if needed: `npm install`
- [ ] Run dev server: `npm run dev`
- [ ] Verify build: `npm run build` (must succeed)
- [ ] Verify lint: `npm run lint` (must pass)
- [ ] Verify types: `npm run typecheck` (must pass — strict mode, zero errors)
- [ ] Verify tests: `npm test` (must pass)

If any pre-flight step fails → **immediate `request_changes`** with reproduction steps. Don't proceed to checklist.

---

## A. Tokens compliance (P0 — blocks PR)

- [ ] **A1.** Zero inline hex colors in JSX/TSX/CSS files (grep: `#[0-9a-fA-F]{3,8}`)
- [ ] **A2.** Zero arbitrary Tailwind values for colors (grep: `text-\[#`, `bg-\[#`, `border-\[#`)
- [ ] **A3.** Zero arbitrary Tailwind values for spacing (grep: `[pmgsh]-\[\d+px\]`, `[wh]-\[\d+px\]`)
- [ ] **A4.** All spacing уses scale tokens (`p-4` not `p-[14px]`; `gap-6` not `gap-[24px]`)
- [ ] **A5.** All font-sizes from type scale (no `text-[15px]`)
- [ ] **A6.** All radius from radius scale (no `rounded-[10px]`)
- [ ] **A7.** All shadows from shadow scale (no inline `box-shadow:` with custom rgba)
- [ ] **A8.** All z-index values from z-index scale (no `z-[999]`)
- [ ] **A9.** Dark mode renders correctly (toggle `[data-theme="dark"]` on `<html>` — verify visually)
- [ ] **A10.** Light mode renders correctly (toggle `[data-theme="light"]` — verify visually)
- [ ] **A11.** No reliance on `prefers-color-scheme` alone — explicit `data-theme` attribute must work
- [ ] **A12.** Semantic CSS variables used (`--bg-primary`, `--text-secondary`), not raw scale tokens, for surfaces that respond к theme

---

## B. Component inventory compliance (P0 — blocks PR)

- [ ] **B1.** No custom-built buttons — uses `<Button>` from inventory
- [ ] **B2.** No custom-built modals — uses `<Dialog>` from inventory
- [ ] **B3.** No custom-built inputs — uses `<Input>`, `<Textarea>`, `<Select>`, `<Checkbox>`, `<RadioGroup>`
- [ ] **B4.** No custom-built table — uses `<Table>` with TanStack Table
- [ ] **B5.** No custom-built toast/notification — uses Sonner-based `<Toast>`
- [ ] **B6.** No custom-built pagination — uses `<Pagination>`
- [ ] **B7.** Compound components use dot-notation (`<Card.Header>`, `<Dialog.Footer>`, `<Tabs.Trigger>`)
- [ ] **B8.** If `new-components-needed:` declared in PR → PR includes companion update to `component-inventory.md` (otherwise reject)
- [ ] **B9.** No re-implementations of shadcn primitives in feature folders (`frontend/src/features/*`)
- [ ] **B10.** Icons sourced from `lucide-react` only (no `react-icons`, no inline SVG для standard icons)

---

## C. Accessibility WCAG 2.1 AA (P0 — blocks PR)

- [ ] **C1.** All interactive elements keyboard-navigable (Tab/Shift+Tab in logical order)
- [ ] **C2.** Tab order matches visual order (no positive `tabIndex` values)
- [ ] **C3.** Focus indicator visible на every focusable element (uses `--shadow-focus-ring`)
- [ ] **C4.** No `outline: none` without replacement focus style
- [ ] **C5.** All `<img>` have meaningful `alt` (or `alt=""` for decorative)
- [ ] **C6.** Icon-only buttons have `aria-label` (Russian)
- [ ] **C7.** Form inputs paired with `<label htmlFor>` — no label-via-placeholder
- [ ] **C8.** Invalid form fields set `aria-invalid="true"`
- [ ] **C9.** Error messages associated via `aria-describedby` pointing to error id
- [ ] **C10.** Color contrast ≥ 4.5:1 for body text (use browser DevTools or axe)
- [ ] **C11.** Color contrast ≥ 3:1 for large text (≥18px or ≥14px bold)
- [ ] **C12.** Color contrast ≥ 3:1 for non-text UI components (borders, focus rings, icons)
- [ ] **C13.** No reliance on color alone for status (icon + text accompany color cue)
- [ ] **C14.** Modal traps focus while open (Radix handles when used correctly)
- [ ] **C15.** Modal Esc dismisses when `dismissable=true`
- [ ] **C16.** Modal returns focus to invoking element on close
- [ ] **C17.** Modal uses `aria-labelledby` → title, `aria-describedby` → description
- [ ] **C18.** Skip-to-main link present as first focusable in `AppShell`
- [ ] **C19.** Tooltips do not contain critical information (must be available elsewhere)
- [ ] **C20.** Loading states use `aria-busy="true"` + `aria-live="polite"` on container
- [ ] **C21.** Toast notifications use `role="status"` (info/success) or `role="alert"` (warning/danger)
- [ ] **C22.** Table headers use `<th scope="col">` (or scope="row" where applicable)
- [ ] **C23.** Sortable table headers set `aria-sort="ascending" | "descending" | "none"`
- [ ] **C24.** Breadcrumb wrapped in `<nav aria-label="Breadcrumb">`, current page uses `aria-current="page"`
- [ ] **C25.** Pagination wrapped in `<nav aria-label="Pagination">`, current page uses `aria-current="page"`
- [ ] **C26.** Respect `prefers-reduced-motion: reduce` — non-essential transitions disabled
- [ ] **C27.** Tested with keyboard only (no mouse) — all flows complete

**Tooling:** Run axe DevTools browser extension or `npm run a11y` (if configured). Zero serious/critical violations required.

---

## D. Responsive design (P0)

- [ ] **D1.** Tested at `sm` (640px), `md` (768px), `lg` (1024px), `xl` (1280px), `2xl` (1536px)
- [ ] **D2.** No horizontal scroll < 1280px (except deliberately wide table containers с explicit scroll affordance)
- [ ] **D3.** Touch targets ≥ 44×44px on mobile (`<md`)
- [ ] **D4.** Sidebar collapses к drawer < `md` breakpoint
- [ ] **D5.** Modals respect viewport bounds (no overflow off-screen on mobile)
- [ ] **D6.** Forms reflow к single-column on `<md`
- [ ] **D7.** Tables degrade gracefully on mobile (horizontal scroll OR card-style rows)

---

## E. Internationalization (P1)

- [ ] **E1.** All copy через i18n keys (no hardcoded Russian/English strings in JSX)
- [ ] **E2.** Date/time formatted via `Intl.DateTimeFormat` с user locale
- [ ] **E3.** Currency formatted via `Intl.NumberFormat` с locale + RUB primary
- [ ] **E4.** Numeric values use locale-aware separators (1 234,56 ru-RU vs 1,234.56 en-US)
- [ ] **E5.** No left-to-right-only assumptions (component layouts work с RTL — verified visually if i18n config has Arabic/Hebrew)
- [ ] **E6.** Pluralization handled via i18n library plural rules (не string concat `${n} item${n > 1 ? 's' : ''}`)

---

## F. TypeScript strict (P0)

- [ ] **F1.** No `any` без явного `// eslint-disable-next-line` + justification comment
- [ ] **F2.** No `@ts-ignore` или `@ts-expect-error` without explanation comment
- [ ] **F3.** Props use Zod-derived types где applicable (form schemas)
- [ ] **F4.** No `as unknown as T` double-cast hacks
- [ ] **F5.** Component prop types exported alongside component (`ButtonProps`, `CardProps`)
- [ ] **F6.** Generic components properly typed (Table column defs, etc.)
- [ ] **F7.** Strict null checks honored — no non-null assertions (`x!.y`) without justification

---

## G. State management + data flow (P1)

- [ ] **G1.** Form state uses `react-hook-form` (not `useState` for forms)
- [ ] **G2.** Form validation uses `zod` schemas
- [ ] **G3.** Server state uses TanStack Query (`useQuery` / `useMutation`)
- [ ] **G4.** Empty / loading / error states all handled explicitly for fetched data
- [ ] **G5.** No prop drilling > 3 levels — use context or composition
- [ ] **G6.** No unnecessary `useEffect` for derived state (use `useMemo` or computed values)

---

## H. Performance (P1)

- [ ] **H1.** No unnecessary re-renders (verify with React DevTools Profiler on interactive surfaces)
- [ ] **H2.** Images use `<img loading="lazy">` for below-fold OR `<picture>` + WebP/AVIF
- [ ] **H3.** Bundle size impact < 50KB gzipped per new component (verify via `vite build --report`)
- [ ] **H4.** Above-the-fold LCP < 2.5s on simulated 4G (Lighthouse)
- [ ] **H5.** No layout shifts (CLS < 0.1) — skeletons preserve layout dimensions
- [ ] **H6.** Heavy components lazy-loaded via `React.lazy` + `<Suspense>` (Wave 1+ if needed)
- [ ] **H7.** TanStack Query stale-time configured (no thrashing refetches)

---

## I. Code quality (P1)

- [ ] **I1.** Components < 200 lines (split into sub-components if exceeded)
- [ ] **I2.** Single responsibility per component
- [ ] **I3.** No `console.log` left in production code
- [ ] **I4.** No commented-out code blocks
- [ ] **I5.** Meaningful component + variable names (no `Comp1`, `data2`, `tmp`)
- [ ] **I6.** JSDoc on public component exports (purpose + non-obvious props)
- [ ] **I7.** Co-located tests follow `<component>.test.tsx` naming

---

## J. Tests (P0 for new features)

- [ ] **J1.** Unit tests for component logic (Vitest + Testing Library)
- [ ] **J2.** Accessibility tests using `jest-axe` or equivalent (zero violations)
- [ ] **J3.** Keyboard interaction tests (Tab, Enter, Esc, arrow keys где relevant)
- [ ] **J4.** Empty / loading / error states tested for data-driven components
- [ ] **J5.** Visual regression tests (Wave 1+ — deferred for now)
- [ ] **J6.** Coverage ≥ 80% for new files (line + branch)

---

## K. Security (P0)

- [ ] **K1.** No `dangerouslySetInnerHTML` без explicit sanitization (DOMPurify or equivalent)
- [ ] **K2.** External links use `rel="noopener noreferrer"` if `target="_blank"`
- [ ] **K3.** User input validated client-side via zod schemas (in addition to server validation)
- [ ] **K4.** No secrets / API keys hardcoded в frontend code
- [ ] **K5.** File path inputs sanitized (no directory traversal possible)
- [ ] **K6.** No `eval()` или `new Function()` usage

---

## Verdict format (per ADR-027)

After completing checklist, emit one of three verdicts:

### ✅ approve
- All P0 items passed
- P1 items either passed OR explicitly deferred с follow-up phase referenced
- Tests green, build clean
- Comment: `LGTM — все P0 пройдено. P1 deferred: <list>` (if applicable)

### 🔄 request_changes
- Any P0 item failed → block
- Create `.planning/revisions/<phase>-reviewer-frontend.md` с numbered findings:
  ```markdown
  # Revision request — <phase-id> — reviewer-frontend — round N/3

  ## Blocking issues (P0)
  1. **A1** (tokens): Inline hex `#0f172a` найден в `src/features/auth/LoginForm.tsx:45` → use `text-primary` semantic class
  2. **C6** (a11y): Icon button `<Button size="icon">` без `aria-label` в `src/components/Header.tsx:23`
  3. **B1** (inventory): Custom `<button className="...">` в `LoginForm.tsx:78` → replace с `<Button variant="primary">`

  ## Non-blocking (P1)
  - **E1** (i18n): Hardcoded Russian text "Войти" — wrap в `t('auth.login.submit')`
  ```
- Max **3 revision rounds**. After 3rd round still failing → escalate.

### 🚨 escalate
- Issue touches design-system invariant (token semantics, component contract change)
- After 3 failed revision rounds
- Disagreement between designer + reviewer that can't be resolved in PR comments
- Escalation goes к founder с context bundle:
  - Original spec
  - All revision rounds (designer outputs + reviewer feedback)
  - Diagnosis paragraph: что именно блокирует консенсус
  - Proposed resolution paths (2-3 options)

---

## Quick reference commands

```bash
# Grep for inline hex colors
grep -rE "#[0-9a-fA-F]{3,8}" frontend/src --include="*.tsx" --include="*.css"

# Grep for arbitrary Tailwind color values
grep -rE "(text|bg|border)-\[#" frontend/src --include="*.tsx"

# Grep for arbitrary spacing
grep -rE "[pmgs]-\[\d+px\]" frontend/src --include="*.tsx"

# Run all gates
npm run lint && npm run typecheck && npm test && npm run build
```

---

## References

- **ADR-027** — Review tiers, max 3 revisions, escalation protocol
- **ADR-026** — Vertical expertise (UI consistency across verticals)
- **ADR-001** — Frontend stack (Vite + React 19 + TanStack + shadcn + Tailwind v4)
- **DECISION-4** — Nordic Warm design philosophy
- `_meta/ui/design-tokens.md` — token contracts
- `_meta/ui/component-inventory.md` — allowed components
- `_meta/ui/UI-DESIGN-PLAYBOOK.md` — designer workflow + ui-ux-pro-max invocation prompts (renamed from CLAUDE-DESIGN-PROMPTS.md per Session 4 / P-DESIGN-1)
- **WCAG 2.1 AA** — https://www.w3.org/WAI/WCAG21/quickref/
- **axe DevTools** — https://www.deque.com/axe/devtools/

---

## Change log

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-13 | Initial Wave 0 checklist. 7 categories, ~85 items. |
