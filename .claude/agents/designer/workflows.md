# designer — workflows

Четыре canonical playbook'а. Каждый — sequence шагов с explicit entry/exit условием и
handoff envelope.

---

## Workflow 1 — New page mock from `ui-spec:`

**Trigger:** inbound CloudEvent `tech.oriion.plan.ui_phase.v1` от `planner` с phase-spec, содержащим non-empty `ui-spec:` block (pages, content-slots, interaction-states, a11y-must-have, components-used, new-components-needed).

**Inputs:**
- Phase-spec.md path + extracted `ui-spec:` YAML excerpt
- PLAN.md (full phase context)
- `_meta/ui/{design-tokens,component-inventory,UI-DESIGN-PLAYBOOK,REVIEW-CHECKLIST}.md`
- Existing related components в `frontend/src/features/<feature>/`

**Steps:**

1. **Load DS context (JIT).** Read `_meta/ui/design-tokens.md` + `component-inventory.md` + `UI-DESIGN-PLAYBOOK.md` + `REVIEW-CHECKLIST.md` полностью (pre-invocation context bundle per UI-DESIGN-PLAYBOOK §3.3). Read phase-spec `ui-spec:` block verbatim.

2. **Validate ui-spec.** Для каждой `pages[]`:
   - Все ли `content-slots` определены (минимум header / main / states)
   - Все ли `interaction-states` перечислены (loading / empty / error / populated + streaming если applicable)
   - `a11y-must-have` non-empty (минимум keyboard-nav + screen-reader-labels + focus-trap для modals)
   - `components-used` ⊆ inventory.md
   - `new-components-needed` либо пустой, либо имеет justification

   Если пробелы — STOP, ask ONE clarifying question planner ДО invocation; не угадывай.

3. **Decide tool route:**
   - **ui-ux-pro-max** (default per P-DESIGN-1) — primary path. Pre-invocation context bundle confirmed loaded.
   - **gsd-ui-researcher subagent** (через Task tool) — spawn если ui-spec ambiguous OR surface novel (нет precedent в features/). Receive recommendations, ОБНОВИ local draft понимания, then invoke ui-ux-pro-max.
   - **Claude Design fallback** — NOT в этом workflow (только §7 UI-DESIGN-PLAYBOOK gate, separate workflow).

4. **Invoke ui-ux-pro-max** per UI-DESIGN-PLAYBOOK §3.2 invocation pattern:
   ```
   Skill(skill="ui-ux-pro-max", args="<verb> <surface> from ui-spec at <phase-id> using inventory <component-list> + tokens semantic roles. Stack: React 19 + TS strict + Vite + TanStack + shadcn/ui + Tailwind v4. Theme: dark-first + light toggle via [data-theme]. Locale: ru-RU. Output: drop-in <ComponentName>.tsx + usage example + a11y notes.")
   ```
   Append relevant subtemplate (Form / List / Detail / State view per UI-DESIGN-PLAYBOOK §4) — pattern-match с phase-spec surface type.

5. **Self-audit per REVIEW-CHECKLIST.** Сверь output:
   - §A (Tokens compliance) — A1-A12 не нарушены
   - §B (Inventory compliance) — B1-B10 не нарушены
   - §C (Accessibility WCAG AA) — C1-C27 covered for relevant interactions
   - §D (Responsive) — D1-D7 для multi-breakpoint surface
   - Если any P0 violation — iterate per §6 UI-DESIGN-PLAYBOOK fix-request template (max 3 rounds, then escalate founder).

6. **(Optional) Preview render.** `mcp__Claude_Preview__preview_start` для HTML preview validation interaction states. Не блокирует handoff если preview infra недоступна.

7. **Compose validation_report** (для handoff payload):
   ```json
   {
     "all_components_in_inventory": true,
     "components_used": ["AppShell", "Card", "Button", "Input", ...],
     "tokens_used_map": {
       "bg-page": ["LoginPage.tsx:12"],
       "text-primary": ["LoginPage.tsx:23", "LoginPage.tsx:45"],
       ...
     },
     "a11y_must_have_addressed": true,
     "a11y_coverage": ["keyboard-nav", "screen-reader-labels", "focus-trap", "reduced-motion"],
     "three_states_present": {"loading": true, "empty": true, "error": true},
     "new_components_needed": [],
     "iteration_count": 1
   }
   ```

8. **Compose handoff event** `tech.oriion.design.mock.v1` envelope per `_shared/handoff-schema.json`:
   - `mocks[]`: paths к .tsx mock files в `frontend/src/features/<feature>/`
   - `validation_report` (from step 7)
   - `recommendations`: hints (e.g. "TanStack Query `staleTime: 60_000` для cells-list", "scroll-restoration на route entry")
   - `phase_id`, `iteration`, `subject`

9. **Persist DS decisions** в `.claude/agents/designer/memory.md` `## DS Decisions`:
   - Vetted patterns (e.g. "auth flow forms — `Card` wrap + `<form>` + submit-loading state via Button.loading")
   - Token decisions (e.g. "added alias `bg-muted` → `--color-base-700` для disabled badges")
   - Rejected approaches с reason (e.g. "Custom Tabs2 — rejected because Radix Tabs covers all cases")

10. **(если new-components-needed not empty)** Open companion PR к `_meta/ui/component-inventory.md` adding new entry с props/states/a11y/tokens; emit `tech.oriion.design.inventory_patch.v1` event к reviewer-frontend для co-sign.

**Outputs:**
- Drop-in `.tsx` mock files
- validation_report JSON
- Updated memory.md
- Optional component-inventory.md PR proposal

**Handoff:** `tech.oriion.design.mock.v1` к `frontend-implementer`.

---

## Workflow 2 — Component variation request

**Trigger:** ad-hoc request от `frontend-implementer` (нужен `Button[variant=ghost-danger]`) OR `architect` (cross-vertical UI variant) OR founder. Event type: `tech.oriion.design.variation_request.v1`.

**Inputs:**
- Request payload: component name, desired variant, justification (use case + why existing variants insufficient)
- `_meta/ui/component-inventory.md` (target entry)
- `_meta/ui/design-tokens.md` (для token availability check)

**Steps:**

1. **Lookup в inventory.** Read `component-inventory.md` target entry. Существует ли вариант уже? Если да — return ad-hoc reply pointing к existing variant; close handoff.

2. **Assess change scope** per UI-DESIGN-PLAYBOOK §2.2:
   - **Additive variant** (e.g. new `variant="ghost-danger"` в `Button` — composable из existing cva): designer LGTM solo route → step 3.
   - **Modifying API** (rename `variant="ghost"` → `variant="subtle"`): consult `architect` через `tech.oriion.conflict.escalation.v1` `conflict_type: ds-modifying-change`.
   - **Removing variant** (deprecate `variant="link"`): enforce 1-wave deprecation cycle, escalate к architect для ADR-revise decision.

3. **(Additive path) Design variant.**
   - Invoke `ui-ux-pro-max` Skill: `"design new variant '<variant>' for <Component> в inventory. Token roles: <list>. States: default / hover / focus / disabled. A11y: <relevant criteria>. Output: cva variant block + props update + tokens map."`
   - Validate token compliance — все color/spacing tokens из existing scale.
   - Validate a11y — focus indicator preserved, contrast ≥3:1 для borders/icons.

4. **Compose inventory patch** — markdown edit к `_meta/ui/component-inventory.md` adding row в variant table + states + tokens used:
   ```markdown
   ### N. <Component>
   ...
   | `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'destructive' \| 'link' \| 'ghost-danger'` | `'primary'` |
   ...
   States: ... | `ghost-danger`: muted danger surface, used для inline destructive-confirm pattern
   ```

5. **Add cva variant code** — output snippet для frontend-implementer (НЕ commit directly — это implementer's role).

6. **Compose handoff** `tech.oriion.design.inventory_patch.v1`:
   - `patch_type: additive`
   - `inventory_diff`: markdown delta
   - `cva_snippet`: code для frontend-implementer
   - `reviewer_co_sign_required: reviewer-frontend`

7. **Persist в memory.** Log variant decision с use-case в `## DS Decisions`.

**Outputs:**
- Inventory patch (markdown delta)
- cva snippet
- Memory entry

**Handoff:** `tech.oriion.design.inventory_patch.v1` к `reviewer-frontend` (co-sign) → `frontend-implementer` (materialize).

---

## Workflow 3 — DS token-change request

**Trigger:** request от founder OR architect для token modification (add new semantic role, rename, deprecate). Event type: `tech.oriion.design.token_change_request.v1`.

**Inputs:**
- Request payload: token name, change type (additive / modifying / removing), rationale, affected surfaces estimate
- `_meta/ui/design-tokens.md` (full current state)
- Blast radius assessment (per UI-DESIGN-PLAYBOOK §2.3)

**Steps:**

1. **Assess blast radius** per UI-DESIGN-PLAYBOOK §2.3:
   - **Color tokens** — high blast (re-renders all surfaces); require visual regression check.
   - **Spacing** — medium blast (layout shifts possible); require Storybook visual diff (Wave 1+).
   - **Type scale** — high blast (line-height interactions); require font-rendering smoke check.
   - **Radius / shadow / motion** — low blast (cosmetic); LGTM designer + reviewer-frontend.

2. **Decide change route:**
   - **Additive** (e.g. `--bg-muted` aliased to `--color-base-700`): designer LGTM solo route → step 3.
   - **Modifying** (e.g. `--text-primary` swap from `base-50` → `base-100`): escalate к `architect` ДО implementation; potential ADR-001 revision check.
   - **Removing** (deprecate `--shadow-deprecated-glow`): enforce 1-wave deprecation cycle:
     - Mark в design-tokens.md с `// @deprecated since: <wave-N> remove: <wave-N+1>`
     - Frontend-implementer adds `// @deprecated` JSDoc в materialization
     - reviewer-frontend flags new uses
     - Removal Wave N+1 via separate PR

3. **(Additive path) Update design-tokens.md.**
   - Add token row to appropriate §2-§9 section
   - Add usage guidance в §10 if non-trivial
   - Increment §12 change log с version bump (0.X.Y patch для additive)
   - Persist DS decision в memory.md с timestamp + use-cases

4. **(Modifying path)** Wait for architect verdict. If approved:
   - Migration playbook entry — какие existing surfaces affected, как migrate (semantic role swap, search-replace pattern)
   - Update design-tokens.md с new value
   - Frontend-implementer schedules migration in subsequent phase (designer не делает silent rewrite)

5. **(Removing path)** Mark token deprecated:
   - Add `// @deprecated` comment в design-tokens.md table
   - Add §12 change log entry "Deprecated <token> — remove Wave N+1"
   - Coordinate с frontend-implementer for usage audit
   - Removal PR на Wave N+1 cycle

6. **Compose handoff** `tech.oriion.design.tokens_patch.v1`:
   - `patch_type: additive | modifying | removing`
   - `tokens_diff`: markdown delta
   - `migration_notes`: для frontend-implementer (если modifying / removing)
   - `reviewer_co_sign_required: reviewer-frontend`
   - `architect_consult_required: <true if modifying/removing>`

7. **Persist в memory.** Decision + blast radius + rationale.

**Outputs:**
- design-tokens.md patch (markdown delta)
- Migration notes (если applicable)
- Memory entry

**Handoff:** `tech.oriion.design.tokens_patch.v1` к `reviewer-frontend` (co-sign) → frontend-implementer (materialize в `frontend/src/styles/tokens.css` per Phase 00.7).

---

## Workflow 4 — Iteration on reviewer feedback (revision cycle)

**Trigger:** inbound `tech.oriion.review.report.v1` со status `request_changes` от reviewer-frontend (или founder) на designer mock. Cycle N of max 3 per ADR-027.

**Inputs:**
- `revisions/<phase>-reviewer-frontend.md` — findings table (file:line, expected, actual, severity)
- Original ui-spec + previous validation_report
- Existing mock files в `frontend/src/features/<feature>/`

**Steps:**

1. **Read revision doc fully.** Each finding: file:line, expected, actual, severity. Don't paraphrase — match exact location.

2. **Group findings:**
   - **Blocker / High** — fix per finding (any P0 REVIEW-CHECKLIST item)
   - **Medium / Low** — fix если cycle < 3 (cleaner exit); defer ОК per founder policy
   - **Disagreement** (finding не consistent с tokens.md / inventory.md) — surface через `tech.oriion.conflict.escalation.v1` к architect, не silent ignore

3. **Compose iteration request** per UI-DESIGN-PLAYBOOK §6 template:
   ```
   # Iteration request — round {{N}} of max 3

   Previous output failed review on:
   - A1: Inline hex `#0f172a` в LoginForm.tsx:45 → use `text-primary`
   - C6: Icon button without `aria-label` в LoginForm.tsx:78
   - B1: Custom <button> вместо <Button> в LoginForm.tsx:92

   Regenerate same component, fixing ONLY these issues. Preserve all other code unchanged. Output format identical to original prompt.
   ```

4. **Invoke ui-ux-pro-max** с iteration prompt. Receive corrected output.

5. **Self-audit again per REVIEW-CHECKLIST.** Если NEW violation introduced — escalate как regression к founder (do not iterate further).

6. **Update memory.md.** Log iteration outcome:
   - What violated
   - Why initial output had violation (pattern detection — это recurring?)
   - Future-proof rule (e.g. "Always specify icon-button `aria-label` explicit в Skill args")

7. **Compose updated handoff** `tech.oriion.design.mock.v1` с `iteration: N`. New mocks[] paths (если file overwritten) + updated validation_report.

8. **Cycle counter check.** Если this is cycle 3 и still failing — DO NOT iterate again. Escalate founder с:
   - Original ui-spec
   - 3 outputs (each round)
   - 3 reviewer reports
   - One-paragraph diagnosis: блокирующий constraint (e.g. "inventory не покрывает required pattern X, нужен new-components-needed")
   - 2-3 proposed resolution paths

**Outputs:**
- Updated mocks с targeted fixes
- Iteration entry в memory.md
- (если max cycle) Founder escalation bundle

**Handoff:** `tech.oriion.design.mock.v1` к `frontend-implementer` (re-handoff) OR `tech.oriion.conflict.escalation.v1` к founder (если cycle 3 failed).

---

## Cross-references

- `system-prompt.md` — invariants + delegation rules
- `checklists/mock-handoff.md` — pre-handoff smoke check
- `checklists/ui-spec-validation.md` — Workflow 1 step 2 validation
- `checklists/tokens-audit.md` — Workflow 3 blast radius audit
- `_meta/ui/UI-DESIGN-PLAYBOOK.md` — full reference
- `_meta/ui/REVIEW-CHECKLIST.md` — self-audit gate criteria
- `_shared/handoff-schema.json` — event envelope schema
