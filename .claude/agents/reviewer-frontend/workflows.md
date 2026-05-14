# reviewer-frontend — workflows

Три canonical playbook'а. Каждый — sequence шагов с explicit entry/exit условием.

---

## Workflow 1 — Tokens + inventory compliance audit

**Trigger:** inbound `tech.oriion.code.commit.v1` от `frontend-implementer`. Cycle 1
(initial review) OR cycle N (post-revision re-review).

**Inputs:**
- Handoff envelope (commit_shas[], changed_files[], tokens_used_map, components_used[], test_coverage_report, bundle_size_delta, phase_id, iteration, a11y_audit_summary)
- `_meta/ui/{design-tokens,component-inventory,REVIEW-CHECKLIST}.md`
- `git diff main...HEAD` (feature-branch scope)
- Build config (tsconfig.json, tailwind.config.ts)

**Steps:**

1. **Pre-flight setup** per `checklists/pr-review-frontend.md` §Pre-review setup:
   ```bash
   git fetch origin <branch>
   git checkout <branch>
   npm install
   npm run build          # must succeed
   npm run lint           # must pass
   npm run typecheck      # zero errors (strict mode)
   npm test               # all pass
   ```
   Если any fails — **immediate request_changes** с reproduction steps. Эмит `tech.oriion.review.report.v1` `verdict: request_changes` `cycle: N`, NEW revision doc с pre-flight failure section. Не proceed.

2. **Scope determination.** `git diff main...HEAD --stat` → list changed files. Filter к `frontend/src/**` + relevant config. Skip backend / contract files (out of reviewer-frontend scope).

3. **§A Tokens compliance audit.** Per `pr-review-frontend.md` §A1-§A12:

   a. **Grep scan inline hex:**
      ```bash
      grep -rnE "#[0-9a-fA-F]{3,8}" frontend/src --include="*.tsx" --include="*.css"
      ```
      Each match (excluding shadcn primitive sources, comments) → finding §A1.

   b. **Grep scan arbitrary Tailwind values:**
      ```bash
      grep -rnE "(text|bg|border)-\[#" frontend/src --include="*.tsx"
      grep -rnE "[pmgs]-\[\d+(\.\d+)?(px|rem)\]" frontend/src --include="*.tsx"
      grep -rnE "rounded-\[\d+px\]" frontend/src --include="*.tsx"
      ```
      Each match → finding §A2-§A6.

   c. **Dark/light mode validation:**
      - Toggle `[data-theme="dark"]` на root element в browser preview
      - Toggle `[data-theme="light"]` — verify visually
      - Если surface broken в one theme — finding §A9/§A10.

   d. **Semantic role tokens check.** Grep raw scale tokens где semantic role expected:
      ```bash
      grep -rnE "(bg|text|border)-(slate|amber|emerald|rose|blue)-\d{2,3}" frontend/src/features --include="*.tsx"
      ```
      Raw scale usage в feature code (vs primitives) → finding §A12.

4. **§B Inventory compliance audit.** Per `pr-review-frontend.md` §B1-§B10:

   a. **Custom buttons grep:**
      ```bash
      grep -rnE "<button " frontend/src --include="*.tsx" | grep -v "frontend/src/components/ui/button/"
      ```
      Each match (excluding shadcn primitive source) → finding §B1.

   b. **Custom modals grep:**
      ```bash
      grep -rnE "position: (fixed|absolute).*z-\[" frontend/src --include="*.tsx"
      ```
      Custom modal pattern → finding §B2.

   c. **Custom inputs:** grep `<input` not via `<Input>` import → §B3.

   d. **Icon source check:**
      ```bash
      grep -rnE "from ['\"](react-icons|@heroicons)" frontend/src --include="*.tsx"
      ```
      Non-lucide icons → finding §B10.

   e. **Compound dot-notation check:**
      ```bash
      grep -rnE "<(Card|Dialog|Tabs)Header" frontend/src --include="*.tsx"
      ```
      Non-dot-notation compound usage → finding §B7.

5. **§F TypeScript strict audit.** Per `pr-review-frontend.md` §F1-§F7:

   a. **`any` grep:**
      ```bash
      grep -rnE ":\s*any[\s,)]" frontend/src --include="*.tsx" --include="*.ts" | grep -v "// eslint-disable"
      ```

   b. **`@ts-ignore` grep:**
      ```bash
      grep -rnE "@ts-(ignore|expect-error)" frontend/src --include="*.tsx" --include="*.ts"
      ```
      Each without explanation comment → finding §F2.

   c. **Non-null assertion grep:**
      ```bash
      grep -rnE "!\.[a-zA-Z_]" frontend/src --include="*.tsx" --include="*.ts" | grep -v "// .*safe:"
      ```

6. **§I Code quality audit** (P1):

   a. **Component size check:**
      ```bash
      wc -l frontend/src/features/**/*.tsx | sort -rn | head -10
      ```
      Any >200 lines → finding §I1.

   b. **`console.log` grep:**
      ```bash
      grep -rnE "console\.(log|debug)" frontend/src --include="*.tsx" --include="*.ts" | grep -v "// debug:"
      ```

7. **Compose findings table** в memory:
   ```
   | ID | Category | Severity | File:line | Expected | Actual |
   |----|----------|----------|-----------|----------|--------|
   | F1 | §A1 tokens | P0 | features/auth/LoginForm.tsx:45 | text-primary | #0f172a |
   ```

8. **Decide verdict:**
   - **All P0 passed + ≤2 minor P1 deferred** → `verdict: approve`
   - **≥1 P0 failed** → `verdict: request_changes`
   - **DS-keeper conflict OR cycle 3 fail** → `verdict: escalate`

9. **(если request_changes)** Compose revision doc:
   ```bash
   mkdir -p revisions
   ```
   Write `revisions/<phase-id>-reviewer-frontend.md` per system-prompt revision doc format.

10. **Persist memory.** В `agent-memory:reviewer-frontend`:
    - Recurring pattern (e.g. "auth feature misses aria-label на icon-only logout — 3rd occurrence")
    - False-positive learning (e.g. "axe `aria-required` warning on disabled inputs — accepted per shadcn pattern")
    - Bundle delta trend (e.g. "Phase 00.7 +50KB → monitor")

11. **Emit handoff** `tech.oriion.review.report.v1`:
    ```json
    {
      "verdict": "request_changes",
      "cycle": 1,
      "findings_count": {"blocker": 3, "high": 0, "medium": 2, "low": 1},
      "revision_doc_path": "revisions/00.7-reviewer-frontend.md",
      "co_review_summary": {
        "security_overlap": ["F1.K3 client validation missing — see reviewer-security"]
      }
    }
    ```

**Outputs:**
- Verdict event
- Revision doc (если request_changes)
- Memory entries

**Handoff:** к `frontend-implementer` (если request_changes) OR к `verifier` (если approve) per pipeline template.

---

## Workflow 2 — Accessibility WCAG 2.1 AA deep audit

**Trigger:** inbound `tech.oriion.code.commit.v1` с `a11y_audit_summary.severity_critical > 0`
OR явный request от founder для deep a11y pass. Co-runs с Workflow 1 (not replacement).

**Inputs:**
- Same as Workflow 1
- `a11y_audit_summary` from handoff (axe-core / jest-axe automated results)
- `_meta/ui/REVIEW-CHECKLIST.md` §C (27 a11y items)
- Browser preview environment (dev server running)

**Steps:**

1. **Pre-flight verification** (must already pass per Workflow 1 step 1).

2. **Automated axe-core scan.** В browser preview mode:
   ```bash
   npm run dev
   # затем в browser DevTools axe extension → "Analyze"
   ```
   OR programmatic:
   ```bash
   npx axe-cli http://localhost:5173/<route> --tags wcag2a wcag2aa
   ```
   Zero serious/critical violations required (P0 §C). Each violation → finding.

3. **Keyboard navigation audit** (manual, per page):
   - Tab through всех interactive elements — verify logical order matches visual
   - Tab visibility — focus indicator visible на каждом element (`--shadow-focus-ring`)
   - Shift+Tab reverse order works
   - Enter / Space activate buttons
   - Esc closes modals (returns focus к trigger)
   - Arrow keys navigate within combobox / radio group / tabs

   Findings — §C1-§C5, §C14-§C17.

4. **Screen reader audit** (NVDA Windows / VoiceOver macOS):
   - Form inputs — label announced correctly
   - Error messages — read via `aria-describedby` after invalid
   - Modal — title announced via `aria-labelledby`, content via `aria-describedby`
   - Toasts — `role="status"` (info/success) или `role="alert"` (warning/danger)
   - Table — headers announced с column / row scope, `aria-sort` для sortable
   - Pagination — `aria-current="page"` для active

   Findings — §C6-§C9, §C21-§C25.

5. **Color contrast audit:**
   - DevTools color picker — sample text-on-surface combinations
   - Body text ≥4.5:1
   - Large text (≥18px or ≥14px bold) ≥3:1
   - Non-text UI (borders, focus rings, icons) ≥3:1

   Findings — §C10-§C13.

6. **Reduced motion audit:**
   - Toggle OS reduced-motion (System Settings)
   - Verify non-essential transitions disabled
   - Skeleton pulse — disabled if reduced-motion
   - Toast slide-in — opacity fade only (≤150ms)

   Findings — §C26.

7. **Compose a11y findings table** (subset of Workflow 1 step 7).

8. **Verdict integration.** A11y findings merged в overall verdict (Workflow 1 step 8).

9. **Persist memory.** Project-specific a11y patterns:
   - Accepted exceptions (e.g. "decorative SVG `aria-hidden` enforced via cva variant")
   - Recurring violations (e.g. "form errors lack aria-describedby — auth feature × 3 cycles")
   - Tooling notes (e.g. "axe-cli misses focus-trap leaks — manual NVDA pass required")

**Outputs:**
- A11y findings list (merged into Workflow 1 verdict)
- Memory entries

**Handoff:** integrated с Workflow 1 verdict.

---

## Workflow 3 — Component inventory conformance audit

**Trigger:** inbound `tech.oriion.code.commit.v1` с suspected new-component need (handoff envelope `validation_report.new_components_needed` non-empty) OR architect-flagged cross-feature pattern duplication. Co-runs с Workflow 1.

**Inputs:**
- Same as Workflow 1
- `_meta/ui/component-inventory.md` (target gate)
- `frontend/src/components/ui/` (materialized primitives)
- `frontend/src/features/**/*.tsx` (consumption sites)

**Steps:**

1. **Inventory consumption audit.**
   - For each component declared в `components_used[]` from handoff — verify import comes from `frontend/src/components/ui/<kebab-name>/`, not feature-scope re-implementation.
   - Grep:
     ```bash
     grep -rnE "import .* from ['\"]@/components/ui/" frontend/src/features --include="*.tsx"
     ```
     Cross-reference с `_meta/ui/component-inventory.md` items.

2. **Custom-built component detection.**
   - Pattern: feature-scope file (`features/<feature>/<Component>.tsx`) с >50 lines + extensive `cva` variants OR Radix primitive imports — может быть custom built где inventory item should be used.
   - Grep:
     ```bash
     grep -rnE "from ['\"]@radix-ui/" frontend/src/features --include="*.tsx"
     ```
     Radix imports в features (not via inventory primitives) → finding §B9.

3. **`new-components-needed:` validation.**
   - Если handoff `validation_report.new_components_needed` non-empty:
     - Verify companion PR к `_meta/ui/component-inventory.md` exists (open OR merged)
     - Reject PR если new component материализован в `frontend/src/components/ui/` без inventory entry
   - Эмит finding §B8 если companion PR missing.

4. **Cross-feature pattern detection.** Identify ≥2 features с similar local utility components (`features/A/SomeFormField.tsx` + `features/B/SomeFormField.tsx`):
   - Cross-grep:
     ```bash
     find frontend/src/features -name "*.tsx" -exec basename {} \; | sort | uniq -d
     ```
   - Recommendation (not blocker — P1): suggest extraction к `frontend/src/components/ui/` (via inventory PR) OR `frontend/src/lib/`.

5. **Compose findings.** Merge с Workflow 1 findings table.

6. **(если new component required)** Escalate к `designer` через `tech.oriion.conflict.escalation.v1`:
   ```json
   {
     "conflict_type": "ds-gap-blocking-review",
     "phase_id": "00.7",
     "missing_component": "Tooltip",
     "consumption_sites": [
       "frontend/src/features/cells/CellHeaderActions.tsx:34",
       "frontend/src/features/tasks/TaskActionMenu.tsx:51"
     ],
     "suggested_action": "Inventory PR — add Tooltip per Radix Tooltip primitive"
   }
   ```

7. **Persist memory.** Pattern recognition (e.g. "Tooltip pattern needed Wave 0 — was deferred к Wave 1, escalate retroactively").

**Outputs:**
- Inventory conformance findings (merged into Workflow 1)
- DS gap escalation event (если applicable)
- Memory entries

**Handoff:** integrated с Workflow 1 verdict; designer DS escalation parallel.

---

## Cross-references

- `system-prompt.md` — invariants + delegation rules
- `checklists/pr-review-frontend.md` — primary gate execution
- `checklists/a11y-axe-runbook.md` — Workflow 2 deep audit runbook
- `_meta/ui/REVIEW-CHECKLIST.md` — gate criteria (co-owned source-of-truth)
- `_meta/ui/{design-tokens,component-inventory,UI-DESIGN-PLAYBOOK}.md` — DS context
- `_shared/handoff-schema.json` — event envelope schema
- ADR-027 — review tiers, max 3 cycles, escalation
