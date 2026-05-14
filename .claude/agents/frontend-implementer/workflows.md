# frontend-implementer — workflows

Три canonical playbook'а. Каждый — sequence шагов с explicit entry/exit условием и
atomic commit decomposition.

---

## Workflow 1 — Implement page from designer mock

**Trigger:** inbound CloudEvent `tech.oriion.design.mock.v1` от `designer` с
`mocks[]` + `validation_report` + `recommendations`.

**Inputs:**
- Handoff envelope (mocks paths, validation_report, recommendations, phase_id, iteration)
- Phase-spec.md + PLAN.md (full context)
- DS sources (`_meta/ui/{design-tokens,component-inventory,REVIEW-CHECKLIST}.md`)
- Existing frontend codebase (`frontend/src/{components,features,routes,api,stores,hooks}/`)
- Build config (tsconfig.json, tailwind.config.ts, vite.config.ts)

**Steps:**

1. **Validate handoff envelope.** Перед материализацией:
   - `validation_report.all_components_in_inventory == true`
   - `validation_report.a11y_must_have_addressed == true`
   - `validation_report.three_states_present.{loading,empty,error} == true` (для data-driven surfaces)
   - `validation_report.new_components_needed == []` (если non-empty — block, escalate к designer)
   - Если any false → emit `tech.oriion.handoff.error.v1` к designer с specific failures; don't materialize.

2. **Load codebase context (JIT).** Read:
   - Each mock file в `mocks[]` (drop-in `.tsx` content)
   - `frontend/src/components/ui/<used-components>/index.tsx` (shadcn primitives that mock imports)
   - Related existing features `frontend/src/features/<feature>/` (для consistency patterns)
   - `frontend/src/routes/` (relevant route file если page-level mock)
   - tsconfig.json + tailwind.config.ts для build constraints

3. **Plan atomic commits.** Decompose deliverable в 3-7 commits. Typical breakdown для page-level feature:
   - **Commit 1:** Route file + skeleton (`frontend/src/routes/<route>.tsx` with route definition + suspense boundary)
   - **Commit 2:** Page component (`frontend/src/features/<feature>/<PageName>.tsx` materialized from mock)
   - **Commit 3:** Feature-scoped hooks (`frontend/src/features/<feature>/hooks/use<Feature>.ts` — TanStack Query / mutations)
   - **Commit 4:** API client (`frontend/src/api/<resource>.ts` — typed fetch wrapper, queryOptions factory)
   - **Commit 5:** Unit tests (`<Component>.test.tsx` co-located)
   - **Commit 6:** Integration test (`<route>.e2e.test.tsx` или Playwright spec если applicable)
   - **Commit 7 (если нужно):** Storybook stories (Wave 1+, deferred currently)

   Записать план в `phase-state:<phase-id>` namespace (memory).

4. **Execute commits sequentially. For each commit:**

   a. **Write/edit files** per commit scope.

   b. **Run lint:** `npm run lint` через Bash. Fix to clean (zero warnings).

   c. **Run typecheck:** `npm run typecheck` через Bash. Fix to zero errors (strict mode).

   d. **Run relevant tests:** `npm test -- <pattern>` (e.g. `npm test -- LoginPage`). Все pass.

   e. **Self-audit per `checklists/component-impl.md`** для component commits, `test-coverage.md` для test commits, `pr-prep.md` перед final handoff.

   f. **Stage + commit:**
      ```bash
      git add frontend/src/features/auth/LoginPage.tsx
      git commit -m "$(cat <<'EOF'
      feat(auth): add LoginPage materialized from designer mock

      Phase: 00.7
      Pipeline-role: frontend-implementer
      Reviewers: pending
      ADR-refs: ADR-001, ADR-007

      Co-Authored-By: frontend-implementer (Opus) <frontend-implementer@teamly-ai>
      EOF
      )"
      ```

   g. **Update PLAN.md status column** для соответствующих tasks: `IN-PROGRESS` → `DONE`.

5. **Final smoke check (after all commits).**
   - `npm run build` — succeeds, bundle size delta <50KB gzipped per new component
   - `npm run dev` — manual smoke check всех 5 interaction states (loading / empty / error / populated / streaming)
   - `npx playwright test --grep "<feature>"` (если integration tests configured)

6. **Compose outbound handoff** `tech.oriion.code.commit.v1` envelope per `_shared/handoff-schema.json`:
   - `commit_shas[]`: latest commits в feature-branch
   - `changed_files[]`: list of modified files
   - `tokens_used_map`: extracted from JSX (grep for `var(--...)` + Tailwind utilities mapped to tokens)
   - `components_used[]`: list of `frontend/src/components/ui/` imports
   - `test_coverage_report`: `npm run test -- --coverage` summary (line + branch % per file)
   - `bundle_size_delta`: vite build report delta vs main
   - `phase_id`, `iteration` (1 если first cycle, N+1 если revision-loop)
   - `a11y_audit_summary`: axe-core CLI / jest-axe results (zero critical/serious required)

7. **Persist memory** в `agent-memory:frontend-implementer`:
   - Reusable hooks (e.g. `useDebouncedValue<T>`)
   - Repository-specific conventions encountered (e.g. "auth feature uses `useAuthStore` Zustand с persist middleware")
   - Recurring lint-fix patterns

**Outputs:**
- Atomic commits (typically 3-7)
- Updated PLAN.md status
- Memory entries

**Handoff:** `tech.oriion.code.commit.v1` к `reviewer-frontend` ∥ `reviewer-security` (parallel review per pipeline template).

---

## Workflow 2 — Fix from reviewer revision-request

**Trigger:** inbound `tech.oriion.review.report.v1` со status `request_changes` от `reviewer-frontend` или `reviewer-security`. Cycle N of max 3 per ADR-027.

**Inputs:**
- `revisions/<phase>-reviewer-<role>.md` — findings table (file:line, expected, actual, severity)
- Existing commits на feature-branch (через `git log feature/wave-0-phase-NN.M-<slug>`)
- Original phase-spec + handoff envelope от designer (для re-orient)

**Steps:**

1. **Read revision doc fully.** Each finding: file:line, expected, actual, severity. Don't paraphrase — match exact location.

2. **Group findings:**
   - **Blocker (P0 REVIEW-CHECKLIST)** — fix per finding (tokens / inventory / a11y / typescript / security)
   - **High** — fix per finding (responsiveness / state management / tests)
   - **Medium / Low** — fix если cycle < 3 (cleaner exit); defer ОК per founder policy (document deferral в revision doc reply)
   - **Disagreement** (finding не consistent с REVIEW-CHECKLIST OR inventory) — surface через `tech.oriion.conflict.escalation.v1` к architect, не silent ignore

3. **For each finding:**
   - Read cited file:line
   - Apply fix per "expected" description
   - **If fix requires** designer re-iteration (e.g. mock did not implement focus-trap → designer regenerates Dialog wrapper) — pause, emit `tech.oriion.handoff.error.v1` к designer с reference на finding ID, wait for re-handoff
   - **If fix requires** DS gap fill (e.g. need `Tooltip` component not in inventory) — escalate к designer для DS extension PR
   - **Otherwise** — fix in-place, add regression test reproducing the issue (prevent re-regression)
   - Run lint + typecheck + tests

4. **NO `git commit --amend`.** Per ADR-027 §6: новый commit для каждой logical fix group. Commit message:
   ```
   fix(auth): add aria-label to icon-only logout button per reviewer-frontend

   Phase: 00.7
   Pipeline-role: frontend-implementer
   Reviewers: pending (re-review)
   ADR-refs: ADR-001
   Addresses: revisions/00.7-reviewer-frontend.md#finding-3

   Co-Authored-By: frontend-implementer (Opus) <frontend-implementer@teamly-ai>
   ```

5. **Force-push allowed** только с `--force-with-lease`:
   ```bash
   git push --force-with-lease origin feature/wave-0-phase-00.7-frontend-skeleton
   ```
   (per ADR-027 §7 — main protected, feature-branch updatable)

6. **Update PLAN.md status** для re-touched tasks: revert `DONE` → `IN-PROGRESS` → `DONE` после fix.

7. **Per finding self-check** — addressed findings count = total blocker + high. Defer-list documented если medium/low not fixed (с rationale).

8. **Cycle counter check.** Если this is cycle 3 и reviewer still requests changes — STOP, escalate founder с:
   - Original handoff envelope
   - 3 sets of commits (each round)
   - 3 revision reports
   - One-paragraph diagnosis: блокирующий constraint
   - 2-3 proposed resolution paths

**Outputs:**
- New atomic commits для fixes
- Force-push к feature-branch
- Updated PLAN.md
- (если max cycle) Founder escalation bundle

**Handoff:** `tech.oriion.code.commit.v1` к `reviewer-frontend` ∥ `reviewer-security` (re-review) OR `tech.oriion.conflict.escalation.v1` к founder (cycle 3 failed).

---

## Workflow 3 — Refactor component extraction (cross-feature consolidation)

**Trigger:** identified pattern duplication в `frontend/src/features/<A>/` ↔ `frontend/src/features/<B>/`. Either:
- Reviewer-frontend flagged via `tech.oriion.review.report.v1` `recommendation: extract-shared`
- Architect emitted `tech.oriion.refactor.request.v1` с consolidation target
- Self-detected during implementation (rare — typically flag к architect first)

**Inputs:**
- Pattern definition (what is duplicated, where, why shared)
- Target extraction location (`frontend/src/components/ui/` для DS-level OR `frontend/src/hooks/` для logic OR `frontend/src/lib/` для utilities)
- Inventory check — если targeting `frontend/src/components/ui/`, designer must approve via `new-components-needed:` companion PR

**Steps:**

1. **Validate scope.** Extraction должен:
   - Cover ≥2 existing usage sites (avoid premature abstraction)
   - Не cross bounded contexts (per ADR-024 — frontend features mirror backend boundaries)
   - Не invent new DS-level component (designer territory, requires inventory PR)
   - Если scope crosses boundaries — escalate к architect

2. **Plan extraction в atomic commits:**
   - **Commit 1:** Add new shared utility/hook/component (с co-located tests)
   - **Commit 2..N:** Replace each usage site (one feature per commit) — call new shared, remove duplicate
   - **Commit N+1:** Remove now-orphaned duplicates (если applicable)

3. **For each commit:**
   - Read source + target file(s)
   - Apply refactor (preserve behavior — refactor is non-functional change per ADR-027 type=`refactor`)
   - Run lint + typecheck + tests
   - Commit с conventional type `refactor`:
     ```
     refactor(shared): extract useDebouncedValue from auth + cells features

     Phase: 00.7
     Pipeline-role: frontend-implementer
     Reviewers: pending
     ADR-refs: ADR-001
     ```

4. **Coverage validation.** После всех refactor commits — re-run full test suite (`npm test`) + build (`npm run build`). Zero regressions tolerated.

5. **Memory persist.** В `agent-memory:frontend-implementer` — log:
   - Pattern identified
   - Extraction location
   - Future-detection rule (e.g. "if both X and Y use Z pattern → consider extraction после 3rd appearance")

**Outputs:**
- Atomic refactor commits
- Memory entry с pattern recognition rule

**Handoff:** `tech.oriion.code.commit.v1` к `reviewer-frontend` ∥ `reviewer-security` (re-review same as feature impl).

---

## Cross-references

- `system-prompt.md` — invariants + delegation rules
- `checklists/pr-prep.md` — pre-handoff smoke check
- `checklists/component-impl.md` — Workflow 1 step 4 component commit gate
- `checklists/test-coverage.md` — Workflow 1 step 4 test commit gate
- `_meta/ui/REVIEW-CHECKLIST.md` — downstream gate criteria (self-audit reference)
- `_shared/handoff-schema.json` — event envelope schema
- ADR-027 — Git/PR workflow (atomic commits, max 3 revision cycles, force-push policy)
