# UI Design Playbook — Oriion

- **Version:** 0.2.0 (renamed from `CLAUDE-DESIGN-PROMPTS.md` v0.1.0 — content fully rewritten)
- **Audience:** `designer` role (per ADR-023 §1), supported by `frontend-implementer` / `reviewer-frontend`
- **Primary tool:** `ui-ux-pro-max` skill (Skill tool invocation within Claude Code session)
- **Fallback tool:** Claude Design (deferred to Wave 1+ high-fidelity polishing — see §7)
- **Output target:** React 19 + TypeScript strict + Vite + TanStack Router/Query + shadcn/ui + Tailwind v4 (per ADR-001)
- **Locale:** ru-RU primary, en-US secondary

---

## 1. Purpose & policy basis

This playbook is the operational contract for how the `designer` agent produces UI artefacts (mocks, component drafts, ui-spec validations) within Claude Code. It supersedes the prior `CLAUDE-DESIGN-PROMPTS.md` (which framed Claude Design as primary tool) per **Session 4 grill-decision C-D3 + P-DESIGN-1** in `.planning/_meta/GRILL-DECISIONS-ORIION.md`.

**Core policy (P-DESIGN-1):**

1. **Designer-role = design-system keeper.** `_meta/ui/design-tokens.md` и `_meta/ui/component-inventory.md` — authoritative sources. Any change to tokens или inventory MUST flow through designer + PR review (reviewer-frontend co-signs). Designer arbitrates breaking change vs additive change vs convention drift.
2. **Primary tool = `ui-ux-pro-max` skill** invoked via Skill tool inside Claude Code. The skill knows 67 styles, 96 palettes, 57 font pairings, 25 chart types, 13 stacks (React/Next/Vue/Svelte/Tailwind/shadcn/etc.) and integrates with shadcn/ui MCP for component search.
3. **Fallback tool = Claude Design** (external service) — reserved for Wave 1+ high-fidelity hero сцены, marketing pages, illustration-heavy surfaces. Не используется для Wave 0 feature work.
4. **No invention.** Designer не создаёт компоненты "из головы". Composition строится из inventory + tokens; new components requires `new-components-needed:` block + PR companion update.

---

## 2. Designer role — DS-keeper mandate

### 2.1 Authority scope

Designer ВЛАДЕЕТ:

- `_meta/ui/design-tokens.md` — adds / deprecates / refines tokens
- `_meta/ui/component-inventory.md` — admits new components, locks API
- `_meta/ui/UI-DESIGN-PLAYBOOK.md` (THIS FILE) — updates prompt templates, fallback policy
- `_meta/ui/REVIEW-CHECKLIST.md` (co-owned with `reviewer-frontend`) — adjusts gate criteria

Designer CONSULTS on (decides jointly с `reviewer-frontend` + `architect`):

- ADR-001 (frontend stack) — major bumps (React 19→20, Tailwind v4→v5)
- ADR-026 (vertical expertise) — UI surfaces per vertical

Designer DOES NOT own:

- Backend contracts (`_meta/contracts/*`) — owner = `backend-implementer` + `architect`
- Vertical content (`_meta/verticals/*`) — owner = `vertical-prompt-author` (spawned)

### 2.2 Change-arbiter protocol

Когда любая роль предлагает изменение DS (новый token, новый component variant, breaking inventory change):

1. **Proposer** opens PR с `ds-change:` markdown frontmatter в commit message describing intent.
2. **Designer** reviews:
   - **Additive** (new token aliased to existing scale; new optional component variant): designer LGTM solo, `reviewer-frontend` co-signs.
   - **Modifying** (token semantic role change; component prop rename): designer requires `architect` consult; ADR-revision if scope reaches Wave-level invariants.
   - **Removing** (deprecate token; remove component variant): designer enforces **deprecation cycle** — 1 Wave grace period с `// @deprecated` markers + migration playbook entry.
3. **Memory:** designer logs decision в `.claude/agents/designer/memory.md` под `## DS Decisions` section.

### 2.3 Token-change blast radius

Designer оценивает blast radius перед approval:

- **Color tokens** (`--color-*`) — high blast: re-renders all surfaces. Require visual regression check.
- **Spacing scale** (`--space-*`) — medium blast: layout shifts possible. Require Storybook visual diff (Wave 1+).
- **Type scale** (`--text-*`) — high blast: line-height interactions. Require font-rendering smoke check.
- **Radius / shadow / motion** — low blast: cosmetic. LGTM by designer + reviewer-frontend.

---

## 3. Primary workflow — ui-ux-pro-max invocation

### 3.1 When designer invokes ui-ux-pro-max

Whenever a phase-spec `ui-spec:` block lands в designer's queue, OR a frontend-implementer requests a mock, OR `architect` requests UI exploration during planning.

### 3.2 Invocation pattern

Designer uses the Skill tool. Action verbs supported by ui-ux-pro-max: **plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, check**.

```
Skill(skill="ui-ux-pro-max", args="<verb> <surface> from ui-spec at <phase-id> using inventory <component-list> + tokens semantic roles. Stack: React 19 + TS strict + Vite + TanStack + shadcn/ui + Tailwind v4. Theme: dark-first + light toggle via [data-theme]. Locale: ru-RU. Output: drop-in <ComponentName>.tsx + usage example + a11y notes.")
```

### 3.3 Pre-invocation context bundle (mandatory)

Before invoking, designer ensures the following files are in context window (Read first if not):

- [ ] `.planning/_meta/ui/design-tokens.md` — full
- [ ] `.planning/_meta/ui/component-inventory.md` — full
- [ ] `.planning/_meta/ui/REVIEW-CHECKLIST.md` — full (designer self-checks before handoff)
- [ ] `.planning/_meta/ui/UI-DESIGN-PLAYBOOK.md` — this file (subtemplate library §4-5)
- [ ] Phase-spec `ui-spec:` block — verbatim
- [ ] Existing related components from `frontend/src/features/<feature>/` — для consistency
- [ ] `.planning/_meta/GRILL-DECISIONS-ORIION.md` §3 policy P-DESIGN-1 — для constraint awareness

### 3.4 Master prompt (skeleton injected via ui-ux-pro-max args)

ui-ux-pro-max skill internally manages style/palette/pairing decisions, но designer передаёт ОБЯЗАТЕЛЬНЫЕ constraints:

```
You are generating UI for Oriion — a solo-founder + AI-team SaaS for WB-Seller and SMB-segment users in Russia. Users spend 6–12 hours/day in the product, often in evening shifts. Optimize for clarity, scannable density, and zero-friction primary flows.

# Stack constraints (HARD — non-negotiable)
- React 19, TypeScript strict (no `any` without justification).
- Vite as bundler; ESM imports.
- Routing: TanStack Router (file-based — match phase-spec).
- Data fetching: TanStack Query (`useQuery`, `useMutation`).
- Forms: `react-hook-form` + `zod` schema. Never `useState` for form state.
- Styling: Tailwind v4 utility classes only. NO `style={{...}}`. NO arbitrary values (`text-[#xxx]`, `p-[14px]`).
- Components: shadcn/ui primitives only из inventory at `_meta/ui/component-inventory.md`. NO custom buttons/modals/inputs — use `<Button>`, `<Dialog>`, `<Input>`, etc.
- Icons: `lucide-react` exclusively.

# Token constraints (HARD)
- Tokens ONLY from `_meta/ui/design-tokens.md`. Reference via Tailwind utility class mapped to semantic role (e.g., `bg-surface`, `text-primary`, `border-default`). NEVER inline hex.
- Spacing / type / radius / shadow / motion: scale tokens only.
- Both dark and light modes must work — drive surfaces from semantic role tokens (`bg-page`, `bg-surface`, `text-primary`, `border-default`), never raw `slate-900`.

# Component constraints
- USE components from `_meta/ui/component-inventory.md`. Compound: dot-notation (`<Card.Header>`, `<Dialog.Title>`).
- If component NOT in inventory: STOP. Emit `new-components-needed:` YAML block at top of response listing { name, purpose, justification, proposed props, states }. Do not invent inline.

# Accessibility (WCAG 2.1 AA — HARD)
- All interactive elements keyboard-navigable. Tab order matches visual order.
- Focus indicators visible — use `--shadow-focus-ring`, never `outline: none` без replacement.
- Icon-only buttons: required `aria-label` в Russian.
- Forms: every input paired с `<label htmlFor>`. Errors via `aria-describedby`. Invalid: `aria-invalid="true"`.
- Color contrast: body ≥ 4.5:1, large text ≥ 3:1. Never convey state by color alone.
- Modal: focus trap + Esc dismiss + return focus on close.

# Locale + copy
- Primary copy в Russian (ru-RU). Avoid English-loanword UI patterns.
- All user-visible strings через i18n keys: `t('namespace.key')`. Wave 0 placeholder allowed if i18n не yet set up — mark с `// i18n-todo:` comment.
- Date/time: `Intl.DateTimeFormat`. Currency: RUB primary.

# Output format
Return response в this order:
1. `new-components-needed:` (only if applicable — YAML block; иначе omit section).
2. JSX file — full component code в single fenced ```tsx code block. All imports included. Drop-in ready под `frontend/src/features/<feature>/<ComponentName>.tsx`.
3. Usage example — short ```tsx block showing parent render с required props + TanStack Query/Router setup.
4. Accessibility notes — bulleted list of a11y decisions: focus order, ARIA attributes, keyboard interactions, screen-reader-only text.

If request ambiguous, ask ONE focused clarifying question BEFORE generating code. Do not generate placeholder lorem-ipsum content.
```

---

## 4. Subtemplate library

Designer appends ONE relevant subtemplate to the master prompt based on surface type. ui-ux-pro-max will pattern-match against these.

### 4.1 Form view

```
# Subtemplate: Form view
- Form state: `react-hook-form` (`useForm`) + `zod` schema. Define schema first, derive types via `z.infer<typeof schema>`.
- Validation modes: `onTouched` default; `onChange` only для instant-validation (password strength meter).
- Submit button: `<Button type="submit" loading={isSubmitting} disabled={!isValid && isSubmitted}>`. Use `loading` (not `disabled`) so button discoverable during submit.
- Error display: per-field error below input via `<FieldError>` pattern. Top-of-form summary только если multiple async errors aggregate.
- Server errors: surface via `setError` from react-hook-form. Map server field paths to form paths.
- Layout: single-column < md; two-column md+ только когда fields pairwise related.
- Empty submit prevention: dirty-tracked; submit disabled while pristine.
- Esc in modal forms: closes только если no dirty changes; иначе prompt confirm-discard.
- Required indicator: red asterisk + `aria-hidden="true"` + visually-hidden "обязательное поле" suffix.
- Optional indicator: muted "(необязательно)" after label.
```

### 4.2 List / table view

```
# Subtemplate: List / table view
- Data: TanStack Query `useQuery({ queryKey, queryFn })`. Always handle `isLoading` / `isError` / empty `data` explicitly.
- Loading: `<Table loading={true}>` renders skeleton rows; не render empty table briefly.
- Empty: `<EmptyState>` с appropriate copy + primary action ("Создать первую ячейку").
- Error: `<EmptyState variant="danger">` с retry (`refetch()`).
- Pagination: server-side via TanStack Query — query key includes `pageIndex`.
- Sorting: server-side для >100 rows; client-side via TanStack Table для ≤100.
- Filtering: search input above table debounced 250ms; multi-field filters в `<Card>` collapsible.
- Row interaction: clickable rows wrap в `<Link>` (TanStack Router) — full row = hit target. Action menus surface в header toolbar не в cells.
- Bulk: `selectable="multi"` → selection toolbar replaces table header chrome when ≥1 row selected.
```

### 4.3 Detail page

```
# Subtemplate: Detail page
- Layout: header (breadcrumb + title + primary actions) → metadata panel → tabbed content (`<Tabs>`).
- Breadcrumb: shows path back to parent list — always present except top-level routes.
- Title: `<h1 className="text-3xl font-bold">` — exactly one h1 per page.
- Primary actions: right-aligned in header; max 2 buttons + overflow `<Menu>`.
- Metadata panel: compact key-value в `<Card>`. Long values truncate с title attribute for hover.
- Tabs: lazy-mount via `<Tabs.Content forceMount={false}>`.
- Inline edit: click-to-edit с `<Input>` swap; save on blur/Enter; revert on Esc. Optimistic update via mutation `onMutate` snapshot.
- Loading: route-level suspense + `<Skeleton>` matching layout — never blank screen.
- Not-found: distinct 404 surface (не generic empty state) с clear path back.
```

### 4.4 State view (loading / empty / error — REQUIRED on every interactive surface)

```
# Subtemplate: All three states (HARD requirement)
Every data-driven component MUST render distinct UI для:

1. **Loading** — `<Skeleton>` matching final layout, `aria-busy="true"` on container. Skeletons preserve layout — не spinners on initial load.
2. **Empty** — `<EmptyState>` с title + optional description + optional primary action. Copy task-oriented ("Создайте первую ячейку для начала работы") не state-descriptive ("Нет данных").
3. **Error** — distinct from empty. User-friendly message (никогда raw server error), retry (`refetch()`), optional support link. Use `<EmptyState variant="danger">` или inline alert.

Optionally: **Stale** — когда TanStack Query `isStale` and refetching, render subtle "обновление…" without blocking current data.

Reviewer rejects PRs где any of these three states отсутствует на data-driven surface.
```

---

## 5. Anti-patterns (reviewer rejects automatically)

```
- ❌ Inline `style={{ color: '#xxx' }}` — use Tailwind class mapped to token.
- ❌ Arbitrary Tailwind values: `text-[#0f172a]`, `p-[14px]`, `mt-[7px]` — use scale tokens.
- ❌ Custom `<button>` built из `<div>` + `onClick` — use `<Button>`.
- ❌ Custom modal через absolute-positioned `<div>` — use `<Dialog>`.
- ❌ `useState` для form state — use `react-hook-form`.
- ❌ Hardcoded English UI text (`"Submit"`, `"Cancel"`) — use Russian via i18n.
- ❌ Icon-only `<Button>` без `aria-label`.
- ❌ Width в `vh` units except full-page modals или hero sections.
- ❌ `outline: none` без replacement focus indicator.
- ❌ `console.log` или `// TODO` в delivered code без `// i18n-todo:` или equivalent traceable marker.
- ❌ Imports icons из `react-icons` или `heroicons` — use `lucide-react`.
- ❌ New dependency без `new-components-needed:` block.
```

---

## 6. Iteration protocol

When ui-ux-pro-max output fails REVIEW-CHECKLIST, designer iterates via fix-request template:

```
# Iteration request — round {{N}} of max 3

Previous output failed review on (cite REVIEW-CHECKLIST item IDs):
- {{checklist-id}}: {{specific violation, with line reference if possible}}
- ...

Regenerate same component, fixing ONLY these issues. Preserve all other code unchanged. Output format identical to original prompt (sections 1–4). If fix requires structural change that violates another constraint, surface conflict explicitly before regenerating.
```

**Max 3 iterations per component** (per ADR-027 review tiers). After 3 failed rounds, designer escalates to founder с:

- Original spec + `ui-spec:` block
- 3 outputs (each round)
- 3 reviewer reports
- One-paragraph diagnosis of blocking constraint
- 2-3 proposed resolution paths

---

## 7. Claude Design fallback (Wave 1+)

Claude Design (external service) is **NOT** primary tool в Wave 0. It is reserved for:

### 7.1 When to fallback to Claude Design

- **Hero / landing surfaces** (post-Wave-0): marketing-grade visuals beyond functional skeleton
- **Illustration-heavy empty states** (Wave 2+): when stock + lucide-react insufficient
- **Brand-defining moments** (post-OQ-09 resolution): onboarding splash, celebration sequences
- **High-fidelity polish passes** (Wave 1 → Wave 2 transition): tighten visual rhythm на existing feature pages

### 7.2 Fallback gate

Designer requests Claude Design **only** when:

1. ui-ux-pro-max output deemed insufficient quality after 1 iteration round (explicit reason logged в designer/memory.md)
2. Surface qualifies per §7.1
3. `architect` approves fallback (Tier 3+ decision per ADR-027)
4. Output stored as **reference image** в `_meta/ui/reference-screens/<surface>.png` — frontend-implementer translates to code using inventory + tokens (Claude Design output не shipped как code directly)

### 7.3 Claude Design constraints (when fallback active)

Same hard constraints как §3.4 master prompt apply. Claude Design output validated against design-tokens.md before becoming reference. No raw HTML/CSS shipped — always translated through frontend-implementer.

---

## 8. References

- `.planning/_meta/ui/design-tokens.md` — token contracts
- `.planning/_meta/ui/component-inventory.md` — allowed components
- `.planning/_meta/ui/REVIEW-CHECKLIST.md` — gate criteria
- `.planning/_meta/GRILL-DECISIONS-ORIION.md` §3 P-DESIGN-1, §1-§2 Session 4 entry
- `.planning/decisions/ADR-001` (frontend stack)
- `.planning/decisions/ADR-023` (designer role definition)
- `.planning/decisions/ADR-026` (vertical expertise)
- `.planning/decisions/ADR-027` (review tiers, max 3 revisions)
- `ui-ux-pro-max` skill — invoked via Skill tool inside Claude Code session

---

## 9. Change log

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-05-14 | **Rewrite** per Session 4 grill-decision C-D3 + P-DESIGN-1. Primary tool: ui-ux-pro-max skill (was: Claude Design). Designer = DS-keeper mandate formalized. Claude Design = Wave 1+ fallback (§7). File renamed `CLAUDE-DESIGN-PROMPTS.md` → `UI-DESIGN-PLAYBOOK.md` via git rename. |
| 0.1.0 | 2026-05-13 | Initial Wave 0 prompts (Claude Design as primary). Superseded by 0.2.0. |
