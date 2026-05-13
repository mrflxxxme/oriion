# Checklist — test coverage (frontend-implementer)

**Used by:** Workflow 1 step 4 per-commit gate для test commits. Block commit if any P0 fails.

---

## A. Unit tests (P0)

- [ ] **A1.** Co-located file `<Component>.test.tsx` next to `<Component>.tsx`
- [ ] **A2.** Vitest + Testing Library imports (not Jest/Enzyme)
- [ ] **A3.** `describe` для component name + nested `describe` per behavior group
- [ ] **A4.** Happy path covered (renders с valid props, primary interaction works)
- [ ] **A5.** Edge cases covered (empty data, error, boundary inputs)
- [ ] **A6.** `userEvent` для interactions (not `fireEvent` — better simulation of real user)
- [ ] **A7.** Coverage ≥ 80% line + branch для new files (`npm test -- --coverage` summary verified)

## B. Accessibility tests (P0)

- [ ] **B1.** `jest-axe` (или equivalent) imported + `expect(container).toHaveNoViolations()` per major rendering
- [ ] **B2.** Zero serious/critical violations
- [ ] **B3.** Keyboard interaction tests (Tab order, Enter, Esc, arrows где relevant)
- [ ] **B4.** Focus management tests (focus returned after modal close, etc.)

## C. State coverage tests (P0 для data-driven components)

- [ ] **C1.** Loading state test — assert `Skeleton` rendered + `aria-busy="true"`
- [ ] **C2.** Empty state test — assert `EmptyState` rendered с appropriate copy
- [ ] **C3.** Error state test — assert error UI rendered + retry action available
- [ ] **C4.** Populated state test — assert data rendered correctly
- [ ] **C5.** Streaming state test (если SSE component) — assert progressive rendering

## D. TanStack Query integration (P0 если component fetches data)

- [ ] **D1.** `QueryClientProvider` wrapper provided via test-helper
- [ ] **D2.** Fresh `QueryClient` per test (no cache pollution)
- [ ] **D3.** Mock `queryFn` returns Promise (resolved / rejected per test case)
- [ ] **D4.** `waitFor` для async assertions (не `setTimeout`)
- [ ] **D5.** Mutation test cases — `onMutate` / `onError` / `onSuccess` paths

## E. Form tests (P0 если component contains form)

- [ ] **E1.** Render — initial state correct (empty, defaults applied)
- [ ] **E2.** Submit blocked while invalid — `Submit` button disabled OR error displayed
- [ ] **E3.** Submit happy path — `onSubmit` called с validated data
- [ ] **E4.** Field validation — invalid input shows error message
- [ ] **E5.** Server error handling — `setError` mapped to field

## F. Router integration (P0 если component uses TanStack Router)

- [ ] **F1.** `createTestRouter` test-helper used (not real router)
- [ ] **F2.** Route params mocked correctly
- [ ] **F3.** Navigation actions tested (`<Link>` click → route change)
- [ ] **F4.** Route loader integration tested (если applicable)

## G. Test quality (P1)

- [ ] **G1.** Descriptive test names (`it('returns 401 when password mismatched')` not `it('handles error')`)
- [ ] **G2.** One assertion focus per test (или tightly grouped)
- [ ] **G3.** No commented-out test code
- [ ] **G4.** No `.skip` / `.only` left in source
- [ ] **G5.** No `setTimeout` waits (use `waitFor` / `findBy*`)
- [ ] **G6.** Test data factories used для complex fixtures (`mockUser()`, `mockTask()`)

## H. Integration / E2E (P1 — для phase-level acceptance)

- [ ] **H1.** Playwright spec exists для critical user flow (если phase requires)
- [ ] **H2.** Spec uses test data isolation (per-test cell + cleanup)
- [ ] **H3.** Spec covers full flow (e.g. login → submit task → see result)
- [ ] **H4.** Spec runs в CI matrix (chromium минимум)

---

## Verdict

### ✅ Proceed to commit
- All P0 items passed
- Coverage threshold met
- Zero a11y violations

### 🔄 Block commit
- Coverage < 80%
- Critical a11y violation
- Missing state coverage (C1-C5)

### 🤝 Escalate
- Test infra gap (no `createTestRouter` helper) — architect / Phase 00.7 deliverable
- Flaky test detected — flag to architect, investigate

---

## Quick reference commands

```bash
# Run tests with coverage
npm test -- --coverage

# Run single component tests
npm test -- LoginPage

# Run E2E
npx playwright test --grep "<feature>"

# Run a11y suite
npm test -- --testNamePattern="a11y"
```

---

## References

- `.claude/agents/frontend-implementer/workflows.md` Workflow 1 step 4
- `_meta/ui/REVIEW-CHECKLIST.md` §J (Tests) downstream gate
- ADR-001 (Vitest + Testing Library)
