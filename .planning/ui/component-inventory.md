# Component Inventory — Wave 0 Foundation

**Version:** 0.1.0
**Target stack:** shadcn/ui + Radix primitives + Tailwind v4 + React 19 + TypeScript strict (per ADR-001)
**Status:** 18 components defined for Wave 0 — ready for Phase 00.7 materialization
**Owner:** designer role; reviewed by reviewer-frontend
**Source of truth:** THIS FILE for component contracts; implementation lives in `frontend/src/components/ui/<component-name>/`
**Last updated:** 2026-05-13

> Spec-layer document. No new component may be added to the implementation without a corresponding entry here. New-component proposals come via PR with `new-components-needed:` justification block.

---

## Naming & conventions

- **Naming:** PascalCase (`Button`, `EmptyState`). Compound components use dot-notation: `Card.Header`, `Card.Body`, `Card.Footer`, `Dialog.Header`, `Dialog.Footer`.
- **File structure (Phase 00.7):** `frontend/src/components/ui/<kebab-name>/index.tsx` with co-located `<kebab-name>.test.tsx`, `<kebab-name>.stories.tsx` (Storybook deferred to Wave 1).
- **Props contracts:** Use Zod schemas where data flows from API. Component props use plain TS interfaces.
- **Variants:** Implemented via `cva` (class-variance-authority) — standard shadcn pattern.
- **Accessibility:** Every component MUST satisfy WCAG AA. Items below labeled `Accessibility MUST` are blocking for review.

---

## Layout (3)

### 1. AppShell

**Purpose:** Top-level chrome with header, sidebar, main content slot, optional footer.
**shadcn/Radix base:** custom layout primitive (no shadcn equivalent).
**Props:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `sidebarCollapsed` | `boolean` | `false` | Persist via localStorage; controlled or uncontrolled |
| `onSidebarToggle`  | `() => void` | — | Required if controlled |
| `density`          | `'comfortable' \| 'compact'` | `'comfortable'` | Affects header height and padding |

**Slots:** `header`, `sidebar`, `main`, `footer?`.
**States:** `collapsed-sidebar` / `expanded-sidebar` / `mobile-drawer` (sidebar becomes drawer < md).
**Tokens used:** `--bg-page`, `--bg-elevated`, `--border-default`, `--space-4`, `--space-6`, `--z-sticky`.
**Accessibility MUST:** Skip-to-main link; sidebar role=navigation; main role=main; aria-label on sidebar toggle; focus restored to toggle on collapse/expand.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 2. Card

**Purpose:** Container surface for grouped content with consistent elevation.
**shadcn/Radix base:** shadcn `Card`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `variant` | `'default' \| 'elevated' \| 'outlined'` | `'default'` |
| `padding` | `'sm' \| 'md' \| 'lg' \| 'none'` | `'md'` |
| `interactive` | `boolean` | `false` |

**Compound:** `Card.Header`, `Card.Body`, `Card.Footer`.
**States:** `default` / `hover` (interactive) / `loading-skeleton` / `disabled`.
**Tokens used:** `--bg-elevated`, `--border-default`, `--shadow-sm`, `--shadow-md`, `--radius-lg`, `--space-4`, `--space-6`.
**Accessibility MUST:** If `interactive`, `role=button`/`tabIndex=0`, full keyboard support, focus ring via `--shadow-focus-ring`.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 3. Separator

**Purpose:** Visual divider between sections.
**shadcn/Radix base:** Radix `Separator`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `orientation` | `'horizontal' \| 'vertical'` | `'horizontal'` |
| `decorative`  | `boolean` | `true` |

**States:** `default`.
**Tokens used:** `--border-default`, `--space-2`.
**Accessibility MUST:** When `decorative=false`, `role=separator` is announced.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

## Inputs (5)

### 4. Button

**Purpose:** Primary interactive element for actions.
**shadcn/Radix base:** shadcn `Button` (cva-based variants).
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'destructive' \| 'link'` | `'primary'` |
| `size` | `'sm' \| 'md' \| 'lg' \| 'icon'` | `'md'` |
| `disabled` | `boolean` | `false` |
| `loading` | `boolean` | `false` |
| `iconLeft` | `ReactNode` | — |
| `iconRight` | `ReactNode` | — |
| `asChild` | `boolean` | `false` (Radix Slot pattern) |

**States:** `default` / `hover` / `active` / `focused` / `disabled` / `loading`.
**Tokens used:** `--color-primary-500`, `--color-primary-600`, `--color-danger-600`, `--text-sm/base`, `--font-medium`, `--radius-md`, `--space-2/3/4`, `--shadow-focus-ring`, `--duration-fast`.
**Accessibility MUST:** When `iconOnly` (size=icon), `aria-label` REQUIRED; `loading` state announces via `aria-busy=true`; focus ring visible.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 5. Input

**Purpose:** Single-line text input.
**shadcn/Radix base:** shadcn `Input` + native `<input>`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `type` | `'text' \| 'email' \| 'password' \| 'number' \| 'search' \| 'tel' \| 'url'` | `'text'` |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` |
| `disabled` | `boolean` | `false` |
| `invalid` | `boolean` | `false` |
| `prefix` / `suffix` | `ReactNode` | — |

**States:** `default` / `focus` / `invalid` / `disabled` / `read-only`.
**Tokens used:** `--bg-surface`, `--border-default`, `--border-focus`, `--color-danger-600`, `--text-base`, `--radius-sm`, `--shadow-focus-ring`.
**Accessibility MUST:** Associated `<label>` via `htmlFor`; if `invalid`, `aria-invalid=true` + `aria-describedby` pointing to error message.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 6. Textarea

**Purpose:** Multi-line text input.
**shadcn/Radix base:** shadcn `Textarea`.
**Props:** Same as Input, plus:

| Prop | Type | Default |
|------|------|---------|
| `rows` | `number` | `4` |
| `autosize` | `boolean` | `false` |
| `maxLength` | `number` | — |

**States:** Same as Input.
**Tokens used:** Same as Input.
**Accessibility MUST:** Same as Input; if `maxLength` set, show live counter with `aria-live=polite`.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 7. Select

**Purpose:** Dropdown selector, single or multi.
**shadcn/Radix base:** Radix `Select` (single) + custom multi-select wrapper.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `placeholder` | `string` | — |
| `options` | `{ label: string; value: string; disabled?: boolean }[]` | — |
| `multi` | `boolean` | `false` |
| `searchable` | `boolean` | `false` |
| `loading` | `boolean` | `false` |

**States:** `closed` / `open` / `loading-options` / `no-results` / `disabled` / `invalid`.
**Tokens used:** `--bg-elevated`, `--border-default`, `--shadow-md`, `--radius-md`, `--z-dropdown`.
**Accessibility MUST:** Full ARIA combobox pattern (Radix handles); keyboard navigation: Arrow up/down, Enter, Esc, type-ahead; multi-select uses checkboxes with proper announcement.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 8. Checkbox + RadioGroup

**Purpose:** Boolean (checkbox) or single-choice from set (radio) selection.
**shadcn/Radix base:** Radix `Checkbox`, Radix `RadioGroup`.
**Props (Checkbox):**

| Prop | Type | Default |
|------|------|---------|
| `checked` | `boolean \| 'indeterminate'` | `false` |
| `disabled` | `boolean` | `false` |

**Props (RadioGroup):**

| Prop | Type |
|------|------|
| `value` | `string` |
| `onValueChange` | `(value: string) => void` |
| `options` | `{ label: string; value: string; disabled?: boolean }[]` |

**States:** `unchecked` / `checked` / `indeterminate` (checkbox only) / `disabled` / `focus`.
**Tokens used:** `--color-primary-500`, `--border-default`, `--bg-surface`, `--radius-sm`, `--shadow-focus-ring`.
**Accessibility MUST:** Associated label; RadioGroup uses `fieldset`+`legend`; full keyboard support (Space toggle, arrows for radio).
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

## Feedback (4)

### 9. Toast (Sonner)

**Purpose:** Transient notification at corner of viewport.
**shadcn/Radix base:** `sonner` library (standard shadcn integration).
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `variant` | `'info' \| 'success' \| 'warning' \| 'danger'` | `'info'` |
| `duration` | `number (ms)` | `5000` |
| `action` | `{ label: string; onClick: () => void }` | — |
| `dismissible` | `boolean` | `true` |

**States:** `appearing` / `visible` / `dismissing`.
**Tokens used:** Semantic color tokens, `--shadow-lg`, `--radius-md`, `--z-toast`.
**Accessibility MUST:** `role=status` (info/success) or `role=alert` (warning/danger); auto-dismiss respects `prefers-reduced-motion`; never auto-dismiss if `action` provided unless `duration` ≥ 10s.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 10. Dialog (modal)

**Purpose:** Blocking modal for confirmations, forms, focused tasks.
**shadcn/Radix base:** Radix `Dialog`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `open` | `boolean` | — |
| `onOpenChange` | `(open: boolean) => void` | — |
| `size` | `'sm' \| 'md' \| 'lg' \| 'xl' \| 'full'` | `'md'` |
| `dismissable` | `boolean` | `true` |

**Compound:** `Dialog.Header`, `Dialog.Body`, `Dialog.Footer`, `Dialog.Title`, `Dialog.Description`.
**States:** `opening` / `open` / `closing` / `closed`.
**Tokens used:** `--bg-elevated`, `--bg-overlay`, `--shadow-xl`, `--radius-lg`, `--z-modal`, `--z-overlay`, `--duration-normal`, `--easing-emphasized`.
**Accessibility MUST:** Focus trap (Radix handles); Esc dismisses if `dismissable`; focus restored to trigger on close; `aria-labelledby` and `aria-describedby` set to title and description; scroll lock on body.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 11. EmptyState

**Purpose:** Communicate absence of data with guidance for next action.
**shadcn/Radix base:** custom.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `illustration` | `ReactNode` | — |
| `title` | `string` | — (required) |
| `description` | `string` | — |
| `action` | `{ label: string; onClick: () => void }` | — |

**States:** `default`.
**Tokens used:** `--text-muted`, `--text-lg/base`, `--space-6/8`, `--font-medium`.
**Accessibility MUST:** Action button has clear label (no "Click here"); illustration has `aria-hidden=true` if decorative.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 12. Skeleton

**Purpose:** Loading placeholder for content shape preservation.
**shadcn/Radix base:** shadcn `Skeleton`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `variant` | `'text' \| 'circular' \| 'rectangular'` | `'rectangular'` |
| `lines` | `number` | `1` (text variant) |
| `width` / `height` | `string \| number` | — |

**States:** `animated-pulse`.
**Tokens used:** `--color-base-200`/`--color-base-700`, `--radius-sm`/`--radius-full`, `--duration-slow`.
**Accessibility MUST:** Parent container has `aria-busy=true`; respects `prefers-reduced-motion` (no pulse if reduce).
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

## Data display (4)

### 13. Table

**Purpose:** Tabular data with sorting, pagination, optional selection.
**shadcn/Radix base:** shadcn `Table` primitives + TanStack Table for logic.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `columns` | `ColumnDef[]` | — |
| `rows` | `Row[]` | — |
| `sortable` | `boolean` | `false` |
| `pagination` | `{ pageSize, pageIndex, onChange }` | — |
| `selectable` | `'none' \| 'single' \| 'multi'` | `'none'` |
| `density` | `'comfortable' \| 'compact'` | `'comfortable'` |

**States:** `empty` / `loading` / `populated` / `sorting` / `filtered` / `error`.
**Tokens used:** `--border-default`, `--bg-elevated`, `--text-sm`, `--space-3/4`, `--color-primary-100` (row hover/selected).
**Accessibility MUST:** Proper `<table>` semantics; `<th scope="col">`; sortable headers use `aria-sort`; row selection uses checkboxes with `aria-label`; pagination buttons have `aria-label="Page N"`.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 14. Badge

**Purpose:** Compact status or category label.
**shadcn/Radix base:** shadcn `Badge`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `variant` | `'default' \| 'primary' \| 'success' \| 'warning' \| 'danger' \| 'info'` | `'default'` |
| `size` | `'sm' \| 'md'` | `'sm'` |

**States:** `default`.
**Tokens used:** Semantic color tokens (100/500 pairs), `--text-xs`, `--font-medium`, `--radius-full`, `--tracking-wide`.
**Accessibility MUST:** If status-bearing (e.g., "Active"), provide context via surrounding text — color alone insufficient.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 15. Avatar

**Purpose:** User or entity representation.
**shadcn/Radix base:** Radix `Avatar`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `src` | `string` | — |
| `fallback` | `string` (initials, 1-2 chars) | — (required) |
| `size` | `'xs' \| 'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` |
| `status` | `'online' \| 'offline' \| 'away' \| 'busy'` | — |

**States:** `image-loading` / `image-loaded` / `image-error-fallback`.
**Tokens used:** `--radius-full`, `--color-success-500`/`--color-base-500`, `--text-xs/sm/base`.
**Accessibility MUST:** `alt` text on image; status indicator has `aria-label` (e.g., "User is online").
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 16. Tabs

**Purpose:** Switch between related panels of content.
**shadcn/Radix base:** Radix `Tabs`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `defaultValue` | `string` | — |
| `value` / `onValueChange` | controlled pair | — |
| `orientation` | `'horizontal' \| 'vertical'` | `'horizontal'` |

**Compound:** `Tabs.List`, `Tabs.Trigger`, `Tabs.Content`.
**States:** `tab-active` / `tab-inactive` / `tab-disabled` / `tab-focus`.
**Tokens used:** `--color-primary-500` (active indicator), `--border-default`, `--text-sm/base`, `--font-medium`.
**Accessibility MUST:** Radix-handled ARIA tabs pattern; arrow keys navigate; activation mode: auto or manual (per spec).
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

## Navigation (2)

### 17. Breadcrumb

**Purpose:** Hierarchical location indicator.
**shadcn/Radix base:** shadcn `Breadcrumb`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `items` | `{ label: string; href?: string }[]` | — |
| `separator` | `ReactNode` | `/` icon |
| `maxItems` | `number` | `4` (collapse middle to ellipsis) |

**States:** `default`.
**Tokens used:** `--text-sm`, `--text-muted`, `--text-primary` (current page).
**Accessibility MUST:** `nav` element with `aria-label="Breadcrumb"`; current page uses `aria-current=page`; separators have `aria-hidden=true`.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

### 18. Pagination

**Purpose:** Page navigation for lists/tables.
**shadcn/Radix base:** shadcn `Pagination`.
**Props:**

| Prop | Type | Default |
|------|------|---------|
| `currentPage` | `number` | — |
| `totalPages` | `number` | — |
| `pageSize` | `number` | `25` |
| `onPageChange` | `(page: number) => void` | — |
| `showFirstLast` | `boolean` | `true` |

**States:** `default` / `first-page` (prev disabled) / `last-page` (next disabled) / `single-page` (hidden).
**Tokens used:** `--color-primary-500` (current), `--text-sm`, `--radius-md`, `--space-2/3`.
**Accessibility MUST:** `nav` with `aria-label="Pagination"`; current page has `aria-current=page`; disabled buttons have `aria-disabled=true`.
**Inventory status:** [ ] designed | [ ] implemented | [ ] reviewed | [ ] tested

---

## File structure (Phase 00.7 deliverable)

```
frontend/src/components/ui/
  app-shell/
    index.tsx
    app-shell.test.tsx
  button/
    index.tsx
    button.test.tsx
  card/
    index.tsx
    card.test.tsx
  ...
```

Each component exports default + named compound parts. Tests use Vitest + Testing Library (per ADR-001).

---

## New-component request protocol

When a phase requires a component not in this inventory:

1. Designer emits `new-components-needed:` block in `ui-spec` with:
   - Proposed name
   - Justification (why none of 18 existing components fit)
   - Props sketch
   - Accessibility requirements
2. PR for phase MUST include companion update to this file
3. reviewer-frontend blocks merge until inventory entry exists

---

## Out-of-scope (deferred to Wave 1+)

- **RichTextEditor** — Lexical or Tiptap-based; Wave 1 if comment/doc features land
- **FileUpload** — drag-and-drop multi-file widget; Wave 1
- **DatePicker / DateRangePicker** — Wave 1 (vertical-specific need from WB-Seller analytics)
- **ChartContainer** — Wave 2 (analytics dashboards); will wrap Recharts or visx
- **CommandPalette (Cmd+K)** — Wave 1 (post first 10 routes)
- **Drawer (side panel)** — Wave 1 (currently AppShell handles mobile drawer; standalone Drawer deferred)
- **Tooltip** — Wave 1 (used sparingly; Radix `Tooltip` will integrate then)
- **Progress / ProgressCircle** — Wave 1
- **Accordion / Collapsible** — Wave 1

---

## References

- ADR-001 — Frontend stack (Vite + React 19 + TanStack + shadcn/ui + Tailwind v4)
- DECISION-4 — Nordic Warm palette
- `ui/design-tokens.md` — token definitions consumed by all components
- `ui/UI-DESIGN-PLAYBOOK.md` — designer workflow + ui-ux-pro-max invocation prompts referencing this inventory (renamed from CLAUDE-DESIGN-PROMPTS.md per Session 4 / P-DESIGN-1)
- `ui/REVIEW-CHECKLIST.md` — review gates per component
- shadcn/ui: https://ui.shadcn.com
- Radix UI primitives: https://www.radix-ui.com
