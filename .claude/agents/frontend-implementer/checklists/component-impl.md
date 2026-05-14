# Checklist — component implementation (frontend-implementer)

**Used by:** Workflow 1 step 4 per-commit gate для component commits. Block commit if any P0 fails.

---

## Pre-flight (P0)

- [ ] **PF1.** Designer handoff envelope received + validated
- [ ] **PF2.** Target file path resolved (`frontend/src/features/<feature>/<Component>.tsx`)
- [ ] **PF3.** Used shadcn primitives exist в `frontend/src/components/ui/` (или Phase 00.7 deliverable)
- [ ] **PF4.** Tokens used in mock все present в `_meta/ui/design-tokens.md`

---

## A. Tokens compliance (P0 — REVIEW-CHECKLIST §A mirror)

- [ ] **A1.** Zero inline hex colors в file (`grep -E "#[0-9a-fA-F]{3,8}" <file>` returns empty)
- [ ] **A2.** Zero arbitrary Tailwind values (`text-[#`, `bg-[#`, `border-[#`, `p-[Npx]`)
- [ ] **A3.** Spacing — scale tokens only (`p-4` not `p-[14px]`)
- [ ] **A4.** Font-sizes — scale tokens only (`text-base` not `text-[15px]`)
- [ ] **A5.** Radius — scale tokens (`rounded-md` not `rounded-[10px]`)
- [ ] **A6.** Shadow — scale tokens (no inline `box-shadow:`)
- [ ] **A7.** z-index — scale tokens (no `z-[999]`)
- [ ] **A8.** Dark + light mode both verified (toggle `[data-theme]` attribute — manual visual check)
- [ ] **A9.** Semantic role tokens used for surfaces (`bg-page`, `text-primary`) — not raw scale (`bg-slate-900`)

## B. Inventory compliance (P0 — REVIEW-CHECKLIST §B mirror)

- [ ] **B1.** No custom `<button>` — uses `<Button>` from `frontend/src/components/ui/button/`
- [ ] **B2.** No custom modal — uses `<Dialog>` from inventory
- [ ] **B3.** No custom inputs — uses `<Input>`, `<Textarea>`, `<Select>`, `<Checkbox>`, `<RadioGroup>`
- [ ] **B4.** No custom table — uses `<Table>` with TanStack Table
- [ ] **B5.** Compound components — dot-notation (`<Card.Header>`, `<Dialog.Footer>`)
- [ ] **B6.** Icons — `lucide-react` only (no `react-icons`, no inline SVG для standard icons)

## C. Accessibility WCAG AA (P0 — REVIEW-CHECKLIST §C mirror)

- [ ] **C1.** All interactive elements keyboard-navigable (Tab/Shift+Tab logical order)
- [ ] **C2.** Focus indicator visible (`--shadow-focus-ring`)
- [ ] **C3.** No `outline: none` без replacement
- [ ] **C4.** Icon-only buttons — `aria-label` в Russian
- [ ] **C5.** Form inputs paired с `<label htmlFor>`
- [ ] **C6.** Invalid form fields — `aria-invalid="true"` + `aria-describedby` к error id
- [ ] **C7.** Color contrast verified (axe DevTools или DevTools color-picker)
- [ ] **C8.** No reliance on color alone (icon + text accompany)
- [ ] **C9.** Modal — focus trap + Esc dismiss + return focus on close (Radix handles)
- [ ] **C10.** Loading — `aria-busy="true"` on container
- [ ] **C11.** Reduced motion respected (`prefers-reduced-motion: reduce`)

## D. TypeScript strict (P0 — REVIEW-CHECKLIST §F mirror)

- [ ] **D1.** No `any` без `// eslint-disable-next-line` + justification
- [ ] **D2.** No `@ts-ignore` / `@ts-expect-error` без explanation
- [ ] **D3.** Props use Zod-derived types where applicable
- [ ] **D4.** Component prop interface exported (`<Component>Props`)
- [ ] **D5.** Generic components properly typed
- [ ] **D6.** `npm run typecheck` zero errors

## E. State + data flow (P1 — REVIEW-CHECKLIST §G mirror)

- [ ] **E1.** Form state — `react-hook-form`, не `useState`
- [ ] **E2.** Form validation — `zod` schemas
- [ ] **E3.** Server state — TanStack Query (`useQuery` / `useMutation`)
- [ ] **E4.** Empty / loading / error states all handled explicitly
- [ ] **E5.** No prop drilling > 3 levels (refactor если detected)
- [ ] **E6.** No unnecessary `useEffect` (derived state через `useMemo`)

## F. Three states present (P0)

For data-driven components:

- [ ] **F1.** Loading state — `<Skeleton>` matching final layout (не spinner на initial load)
- [ ] **F2.** Empty state — `<EmptyState>` с task-oriented copy + primary action
- [ ] **F3.** Error state — distinct from empty, user-friendly message, retry action

## G. Code quality (P1 — REVIEW-CHECKLIST §I mirror)

- [ ] **G1.** Component < 200 lines (split sub-components если exceeded)
- [ ] **G2.** Single responsibility
- [ ] **G3.** No `console.log` left
- [ ] **G4.** No commented-out code
- [ ] **G5.** Meaningful names (no `Comp1`, `data2`, `tmp`)
- [ ] **G6.** JSDoc on public exports (purpose + non-obvious props)

---

## Verdict

### ✅ Proceed to commit
- All P0 items passed
- P1 items passed OR explicitly deferred

### 🔄 Block commit
- ≥1 P0 item failed
- Fix locally, re-run checklist

### 🤝 Escalate
- Inventory gap (B1-B6 require inventory extension) — designer
- DS-token gap (A items require new token) — designer
- Cross-feature coupling (E5 + cannot extract) — architect

---

## References

- `.claude/agents/frontend-implementer/workflows.md` Workflow 1
- `_meta/ui/REVIEW-CHECKLIST.md` (downstream gate — this is self-mirror)
- ADR-027 (atomic commits)
