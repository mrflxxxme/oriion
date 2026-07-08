---
phase: 01.4-ui
slug: memory-panel
status: implemented
shadcn_initialized: true
preset: none
created: 2026-07-09
tool: frontend-implementer (direct — no designer handoff envelope for this phase)
---

# Phase 01.4-ui — UI Design Contract (Memory panel «Что помнит команда/агент»)

> Design contract for the memory panel frontend, written retroactively alongside implementation
> (Wave-1 phase run without a separate designer handoff — frontend-implementer materialized the
> screen directly from the phase brief + the live `/api/v1/memory/*` API + the existing 18-component
> inventory / v0.2 cool-blue tokens). No new components, no new tokens.

## Intent (one line)

Let any cell member see, search, add, and delete what the team's shared memory and each agent's
personal memory currently hold — read/write surface over the already-live memory API, Wave-0 scope.

---

## Route + navigation

| Item | Value |
|---|---|
| Route | `/memory` (top-level, under the authenticated `AppLayout`, alongside `/cells`) |
| Nav entry | Sidebar link "Память" (Brain icon, `lucide-react`), same pattern as the existing "Ячейки" link |
| Why top-level, not `/cells/$cellId/memory` | The memory API has **no `cell_id` path param** — cell scope comes from the RLS tenant context (`get_current_cell_id`, Wave-0 single-cell-per-user). Nesting under a `cellId` route param would be cosmetic only, so the simpler top-level route was chosen. |

---

## Layout

Single page, two `Tabs` (component-inventory #16):

```
Breadcrumb: Память
H1: Память

[ Tab: Ячейка ] [ Tab: Агент ]
──────────────────────────────
  Search input (label "Поиск по памяти") ... [Сбросить поиск?] [Добавить запись]
  (Agent tab only: Select "Агент" above the search row)
  [ MemoryAddForm — collapsible, closed by default ]
  [ list | skeleton | empty-state | error-state ]
```

Each list row (`MemoryEntryList`):

```
[ title-or-kind ]  [kind Badge]  [source Badge]  [score % — search only]      [Удалить]
content (wrapped, whitespace preserved)
created_at (ru-RU medium date + short time)
```

Delete is a single shared confirmation `Dialog` (component-inventory #10), not one dialog per row.

---

## States (three-states + the extras this surface needs)

| State | Cell tab | Agent tab |
|---|---|---|
| Loading | `Skeleton` bars (`aria-busy` on the wrapping div) while the list query is in flight | `Skeleton` bars while the agents list loads, then the same list skeleton once an agent is selected |
| Empty | `EmptyState` "Пока нет ничего в памяти ячейки" + description | `EmptyState` "Пока нет ничего в памяти агента" once an agent is selected with zero entries |
| Empty (no agents) | n/a | `EmptyState` "Нет доступных агентов" — the cell has no agent instances yet (placeholder, not an error) |
| Error | `EmptyState variant="danger"` + "Повторить" retry button | same, plus a separate error state if the **agents** list itself fails to load |
| Populated | `MemoryEntryList` | same |
| Searching | same list component, hits carry a `score` (rendered as a rounded percentage); empty search shows "Ничего не найдено" (deliberately distinct copy from the base empty state) | same |

---

## Data / interaction contract

- **List:** `GET /memory` (cell) / `GET /memory/agents/{agentId}` (role) — limit 100, no pagination UI yet (Wave-0 volumes are small; `Pagination` component deferred to a follow-up if cell memory grows past ~100 rows).
- **Search:** `GET /memory/search?q=...` / `GET /memory/agents/{agentId}/search?q=...` — fires on every keystroke via TanStack Query's key-based refetch (no explicit debounce yet — P1 follow-up, see Deviations).
- **Add:** `POST /memory` / `POST /memory/agents/{agentId}` via a collapsible `MemoryAddForm` (react-hook-form + zod, `mode: "onSubmit"`). Source is always `"manual"` server-side; the form never sends `source`.
- **Delete:** `DELETE /memory/{entryId}` / `DELETE /memory/agents/{agentId}/{entryId}` behind a confirmation `Dialog`.
- **"Edit":** explicitly out of scope — no PATCH endpoint exists. The contract is delete + re-add with prefilled values (`MemoryAddForm`'s `prefill` prop exists for this but is not yet wired to a row action in this phase — see Deviations).
- **Agent picker (role tab):** `GET /cells/{cellId}/agents` (agents bounded context, not memory) sourced via a new minimal `frontend/src/api/agents.ts` client — see Deviations. `cellId` resolves via the existing `cellsApi.listAllCells()` (same call `CellsListPage` already makes), Wave-0 single-cell.
- **Cache invalidation:** add/delete mutations invalidate the relevant list query key (`["memory","cell"]` or `["memory","role",agentId]`); no optimistic updates (kept simple per brief).

---

## Tokens used

Only semantic role tokens + scale tokens already in `frontend/src/styles/` (v0.2 cool-blue palette, ADR-031/00.8) — no new tokens, no inline hex, no arbitrary Tailwind values:

- Surfaces: `bg-surface`, `border-default`
- Text: `text-primary`, `text-secondary`, `text-tertiary`, `text-danger-600`
- Accent (reserved uses only): `bg-cta`/`text-on-cta` via `<Button variant="primary">`, active-tab indicator via `<Tabs.Trigger>` (Radix `data-[state=active]:border-cta`), `<Badge variant="primary">` not used here (kind/source badges use `default`/`info`/`warning` — no accent overuse)
- Spacing/radius: `gap-3/4/6`, `p-4`, `rounded-md`
- Focus: `--shadow-focus-ring` (inherited from `Button`/`Input`/`Select`/`Dialog` — not hand-rolled)

---

## Accessibility notes (WCAG 2.1 AA — REVIEW-CHECKLIST §C)

- Search `Input` and add-form fields all use `<label htmlFor>` (via `useId`), never placeholder-as-label.
- Content textarea sets `aria-invalid` + `aria-describedby` pointing at a `role="alert"` error message on validation failure (mirrors `TaskSubmitPage`'s pattern).
- Delete confirmation reuses `Dialog` — Radix owns focus trap / Esc / focus-restore / `aria-labelledby`+`aria-describedby`.
- Entry list is a semantic `<ul aria-label="Ячейка"|"Агент">` / `<li>` per row — screen readers get a list landmark and item count.
- Loading regions carry `aria-busy="true"` on the wrapping container (Skeleton bars themselves are `aria-hidden`, per the Skeleton component contract).
- Source/kind conveyed via Badge text labels, never color alone (REVIEW-CHECKLIST C13) — e.g. "Фильтр-агент" badge is legible even without color.
- No color-only status: every badge carries its Russian label.
- Verified with `jest-axe` in `MemoryPanelPage.test.tsx` ("has no axe violations") — 0 serious/critical.

---

## Deviations from the brief (with reasons)

1. **Source badge values** — the brief listed `manual` / `filter_agent` / `conversation_summary`. The actual DB `CHECK` constraint (`backend/src/memory/models.py`) is `source IN ('manual','filter_agent','summary')` — `conversation_summary` is a `kind`, not a `source` (the auto-summarizer writes `kind="conversation_summary", source="summary"`, see `conversation_service.py`). The UI matches the real schema: badges are `Вручную` / `Фильтр-агент` / `Автосводка` for `source`, and `kindLabel()` falls back to the raw string for kinds without copy yet (covers `conversation_summary` and any future kind).
2. **Agent picker data source** — the brief allowed "get available agents however the cells/tasks features already surface them; if none available, role section can show an empty/placeholder state." Neither feature surfaces agents today, but a live, already-shipped endpoint does: `GET /api/v1/cells/{cell_id}/agents` (`backend/src/agents/routers/instances.py`). Added a minimal read-only `frontend/src/api/agents.ts` (mirrors the `cells.ts`/`tasks.ts` client style) to consume it — no backend change. If the cell genuinely has zero agent instances, the placeholder empty state (`Нет доступных агентов`) still applies.
3. **No debounce on search** — every keystroke fires a query (TanStack Query dedupes by key but does not throttle). Acceptable at Wave-0 volumes; flagged as a P1 follow-up rather than adding a `useDebouncedValue` hook not otherwise present in the codebase.
4. **No pagination UI** — `list()`/`listForAgent()` are called with `limit: 100`, no `<Pagination>` wired in yet. Cell/role memory soft caps are 500/200 rows respectively (`CELL_MEMORY_SOFT_CAP`/`ROLE_MEMORY_SOFT_CAP` in `models.py`); Wave-0 usage is expected far below 100. Flagged as a follow-up once real usage approaches the limit.
5. **"Edit" wiring** — `MemoryAddForm` accepts a `prefill` prop (delete + prefill-add, per the brief) but no row action calls it yet in this phase; only fresh "Добавить запись" is wired. The plumbing exists so a follow-up can add an "Изменить" button per row without new component work.
6. **`X-Memory-Soft-Cap-Exceeded` response header** — not surfaced in the UI (no toast/banner on soft-cap breach). The header is advisory-only server-side (entry still stored); flagged as a nice-to-have follow-up, not required for this phase's AC.

---

## 6-pillar self-review (REVIEW-CHECKLIST.md)

- [x] **A. Tokens compliance** — no inline hex, no arbitrary Tailwind values; semantic role tokens only (`grep -rE "#[0-9a-fA-F]{3,8}"` / `(text|bg|border)-\[#` over `frontend/src/features/memory` and `frontend/src/api/{memory,agents}.ts` returns nothing).
- [x] **B. Component inventory compliance** — reuses `Button`, `Dialog`, `Input`, `Textarea`, `Select`, `Checkbox`, `Badge`, `EmptyState`, `Skeleton`, `Tabs`, `Breadcrumb` from `frontend/src/components/ui`; zero hand-rolled buttons/modals/inputs; compound components used via dot-notation (`Dialog.Header`, `Tabs.Trigger`); barrel stays at 18 exports (no new primitive added).
- [x] **C. Accessibility WCAG 2.1 AA** — see notes above; `jest-axe` assertion in the component test, 0 violations.
- [x] **D. Responsive** — layout is a single flex column with `flex-wrap` on the search/toggle row and the entry-row header; no fixed widths beyond `max-w-xs` on the agent Select; no horizontal scroll introduced.
- [~] **E. Internationalization** — all copy through `t()` keys (`memory.*` namespace in `lib/i18n.ts`); dates via `Intl.DateTimeFormat("ru-RU", ...)`. Deferred (matches Wave-0 baseline): no plural-rule handling (no counted strings on this screen) and the flat-dictionary `t()` indirection is the same Wave-0 placeholder used everywhere else in the app.
- [x] **F. TypeScript strict** — no `any`, no `@ts-ignore`; exported prop types (`MemoryAddFormProps`, `MemoryEntryListProps`, `MemorySectionViewProps`); `exactOptionalPropertyTypes`-safe conditional spreads for optional fields, matching the existing `Select`/`Input` component convention.
- [x] **G. State management** — server state via TanStack Query (`useQuery`/`useMutation`) only, no manual `fetch`+`useState`; form state via `react-hook-form` + `zod` (`memoryFormSchema`); all three query states (loading/empty/error) handled explicitly per section.
- [~] **H. Performance** — no debounce on search (see Deviations #3); no virtualization (fine at ≤100 rows); no bundle-size audit run (no new heavy dependency introduced — only existing `react-hook-form`/`zod`/`@tanstack/react-query` already in the app).
- [x] **I. Code quality** — files kept small and single-purpose (`MemoryEntryList.tsx`, `MemoryAddForm.tsx`, `MemorySection.tsx`, `labels.ts`, `hooks.ts`, `MemoryPanelPage.tsx`), all under the 500-line ceiling; no commented-out code; no stray `console.log`.
- [x] **J. Tests** — colocated Vitest + Testing Library tests for the API client (`api/memory.test.ts`, `api/agents.test.ts`), the hooks (`features/memory/hooks.test.ts`), and the page (`features/memory/MemoryPanelPage.test.tsx`: render, add, delete-confirm + cancel, search, empty-agents placeholder, role-memory add, validation error, error+retry, axe). 181/181 tests green, coverage 93.83% lines / 86.3% branch / 79.83% funcs (repo-wide, threshold 70%, not regressed).
- [x] **K. Security** — no `dangerouslySetInnerHTML`; no external links introduced; zod validates client-side on top of server validation; no secrets.

Legend: `[x]` pass, `[~]` pass with a noted, deliberate P1 deferral (see Deviations).

---

## Files

- `frontend/src/api/memory.ts` — typed client, 8 memory endpoints
- `frontend/src/api/agents.ts` — typed client, 1 read-only endpoint (agent picker source)
- `frontend/src/features/memory/{MemoryPanelPage,MemorySection,MemoryEntryList,MemoryAddForm}.tsx`
- `frontend/src/features/memory/{hooks,labels,schemas,format}.ts`
- `frontend/src/app/router.tsx` — `/memory` route
- `frontend/src/app/AppLayout.tsx` — sidebar nav entry
- `frontend/src/lib/i18n.ts` — `memory.*` copy keys

---

## Checker sign-off

Retroactive self-review only (no `gsd-ui-checker` pass requested for this phase) — see the 6-pillar table above for the substitute self-audit.
