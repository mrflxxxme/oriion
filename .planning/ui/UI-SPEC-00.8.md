---
phase: 00.8
slug: design-restyling
status: approved
shadcn_initialized: true
preset: none
created: 2026-06-13
reviewed_at: 2026-06-13
tool: ui-ux-pro-max (per UI-DESIGN-PLAYBOOK §3) + designer DS-keeper
---

# Phase 00.8 — UI Design Contract (professional cool-blue v0.2)

> Visual + interaction contract for the Wave-0 restyle. Per [ADR-031](../decisions/ADR-031-design-direction-restyling.md)
> and the founder bake-off (2026-06-13). **Scope = token VALUES + ADR/spec narrative only.** Token
> names/structure, the 18-component barrel, light theme, and dark-default are FROZEN. No new screens,
> no new components, no relayout — visual/token pass on the existing 6 surfaces.

## Intent (one line)

Shift Wave-0 UI from Nordic Warm (amber) to a **deeper, cooler, professional dark theme with a
Royal-Blue accent** — teamly.to spacious density as the layout reference — so the Wave-1 friends demo
runs on a "grown-up" UI.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn/ui + Radix (existing — unchanged) |
| Component library | radix (18-component inventory, frozen) |
| Icon library | lucide-react (unchanged) |
| Font | Inter (sans) / JetBrains Mono (mono) — **unchanged** (no web-font work this phase) |
| Theme | dark-first (default) + light toggle via `[data-theme]` |
| Materialization | `frontend/src/styles/{tokens.css, themes.css, index.css}` |

---

## Color — the v0.2 palette (PRIMARY DELIVERABLE)

**Founder-locked accent:** Royal Blue `#2563eb` (replaces amber `#f59e0b`). Only **values** change;
token names stay. Hex lives ONLY in `tokens.css` / `index.css` token defs (CI gate §A).

### Role summary (60/30/10)

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0b111e` bg-page / `#060a13` overlay | Page background, deepest surfaces |
| Secondary (30%) | `#141c2b` bg-surface | Cards, sidebar, nav, table chrome |
| **Accent (10%)** | **`#2563eb`** (CTA) + `#60a5fa` (links on dark) | **CTA only, active-tab indicator, links, focus ring** |
| Destructive | `#e11d48` danger-600 | Destructive actions only |

**Accent reserved for:** primary `<Button variant="primary">`, active `<Tabs.Trigger>` indicator,
in-content links, `<Badge variant="primary">`, `<Checkbox>`/`<RadioGroup>` checked, `<Pagination>`
current page, focus ring. **Never** for status, decoration, role pills, sidebar fill, or borders.

### 2.1 Brand / Primary scale (blue — replaces amber)

| Token | v0.1 (amber) | **v0.2 (blue)** | Role |
|-------|------|------|------|
| `--color-primary-100` | `#fef3c7` | `#dbeafe` | Badge bg / primary surface (light chip) |
| `--color-primary-400` | `#fbbf24` | `#60a5fa` | **Links on dark**, dark-mode CTA hover, muted/disabled |
| `--color-primary-500` | `#f59e0b` | `#2563eb` | **Brand CTA** (white text) |
| `--color-primary-600` | `#d97706` | `#1d4ed8` | Light-mode CTA / dark pressed |
| `--color-primary-700` | `#b45309` | `#1e40af` | Active/pressed |

Lightness is monotonic (100 lightest → 700 darkest) so all `brand-*` utilities stay valid.

### 2.2 Base — deepened COOL slate (canvas only; light tints unchanged)

| Token | v0.1 | **v0.2** | Note |
|-------|------|------|------|
| `--color-base-950` | `#020617` | `#060a13` | bg-overlay / modal backdrop (deepest) |
| `--color-base-900` | `#0f172a` | `#0b111e` | **bg-page** — deepened, still cool slate |
| `--color-base-800` | `#1e293b` | `#141c2b` | bg-surface (elevated) |
| `--color-base-700` | `#334155` | `#26324a` | border-default on dark (cooler) |
| `--color-base-600` | `#475569` | `#37445f` | border-emphasis on dark |
| `--color-base-50…500` | — | **unchanged** | Light-mode surfaces + dark text stay as-is |

Hue stays ~218–222° (cold blue-slate) — **not** warmed. Validated by ui-ux-pro-max "Dark Mode (OLED)"
pattern (deep slate `#0F172A`→deeper, `#020617` backdrop, `#F8FAFC` text).

### 2.3 Semantic — resolve the brand↔info COLLISION

Brand is now blue, but `info` was also blue (`#3b82f6`) → they'd merge, breaking single-accent
discipline (design-tokens §10.2). **CONFIRMED in grill (2026-06-13): move `info` → cyan** so the
brand blue stays the only "brand" blue. (`info` is currently unused in all 6 screens — only the
`Badge` `info` variant references the tokens — so this change regresses nothing.)

| Semantic | v0.1 | **v0.2** | Status |
|---|---|---|---|
| `info-100 / 500 / 700` | `#dbeafe / #3b82f6 / #1d4ed8` (blue) | **`#cffafe / #06b6d4 / #0e7490` (cyan)** | **CHANGED — anti-collision** |
| `warning-100 / 500 / 700` | `#fef3c7 / #f59e0b / #92400e` | **unchanged** | Now a *standalone* semantic (no longer "alias to brand amber") |
| `success-100 / 500 / 600 / 700` | emerald | **unchanged** | — |
| `danger-100 / 600 / 700` | rose | **unchanged** | — |

> Net effect: brand = blue (the only brand hue); info = cyan; warning = amber (now independent, not a
> brand alias). Cleaner single-accent system than v0.1.

### 2.4 Dark/light semantic mappings (themes.css) + mode-invariant text

| Role | Dark | Light |
|---|---|---|
| `--bg-page` | base-900 `#0b111e` | base-50 `#f8fafc` |
| `--bg-surface` | base-800 `#141c2b` | base-100 `#f1f5f9` |
| `--bg-overlay` | base-950 `#060a13` | `rgba(11,17,30,0.4)` |
| `--text-primary` | base-50 `#f8fafc` | base-900 `#0b111e` |
| `--text-secondary` | base-300 `#cbd5e1` | base-500 `#64748b` |
| `--text-tertiary` | base-400 `#94a3b8` | base-400 `#94a3b8` |
| `--border-default` | base-700 `#26324a` | base-200 `#e2e8f0` |
| `--border-emphasis` | base-600 `#37445f` | base-300 `#cbd5e1` |
| `--cta-primary` | primary-500 `#2563eb` | primary-600 `#1d4ed8` |
| `--cta-primary-hover` | primary-400 `#60a5fa` | primary-700 `#1e40af` |
| **`--color-on-cta`** | **`#ffffff`** | **`#ffffff`** | was base-900 (dark) — now mode-invariant WHITE (C15) |
| `--color-on-danger` | `#ffffff` | `#ffffff` | unchanged |
| `--shadow-focus-ring` | `0 0 0 3px rgba(37,99,235,0.40)` | same | was amber alpha |

### WCAG AA contrast table (verified)

| Pairing | Ratio | Gate | Verdict |
|---|---|---|---|
| White `#ffffff` on CTA `#2563eb` (dark) | **5.17:1** | ≥4.5 body | ✓ AA |
| White on light-CTA `#1d4ed8` | **6.77:1** | ≥4.5 | ✓ AA (on-cta mode-invariant) |
| Link `cta-hover`=`#60a5fa` on bg-page `#0b111e` (dark) | **~7.4:1** | ≥4.5 | ✓ AA |
| Link `cta-hover`=`#1e40af` on bg-page `#f8fafc` (light) | **~9:1** | ≥4.5 | ✓ AA |
| White on CTA-hover `brand-700 #1e40af` | **9.7:1** | ≥4.5 | ✓ AA |
| CTA `#2563eb` as non-text/large on bg-page | **3.64:1** | ≥3 | ✓ AA |
| Focus ring `rgba(37,99,235,.4)` on dark surface | ≥3 (non-text) | ≥3 | ✓ |
| text-secondary `#cbd5e1` on bg-page | **~11.8:1** | ≥4.5 | ✓ |
| text-tertiary `#94a3b8` on bg-page | **~6.3:1** | ≥4.5 | ✓ |
| info badge `#0e7490` on `#cffafe` | **4.79:1** (tightest pass) | ≥4.5 | ✓ |
| primary badge `#1e40af` on `#dbeafe` | high | ≥4.5 | ✓ |
| success `#047857` / warning `#92400e` / danger `#be123c` on their -100 | high | ≥4.5 | ✓ |

> Re-verify live with axe-core on all 5 routes (AC3) — these are computed values, not a substitute
> for the runtime check (C10–C12).

---

## Spacing Scale

Unchanged (structural tokens frozen). 4px base: `--space-1`=4 … `--space-20`=80.

Exceptions: none. **Polish guidance** (teamly.to spacious density — apply via existing scale tokens,
no arbitrary values):

- Major block rhythm `--space-8`/`-10` (header → tabs → artifact cards); inside cards `--space-6`.
- Section title → content gap consistent `--space-3`.
- Sidebar nav items compact: `--space-2` vertical, icon+label.
- Markdown body line-length ~65–75ch; line-height 1.6–1.7 (`--text-sm`/`-base`).

---

## Typography

Unchanged (no web-font work this phase). Inter + JetBrains Mono, Major-Third scale.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px (`--text-base`) | 400 | 1.5 |
| Label | 14px (`--text-sm`) | 500 | 1.43 |
| Heading (page) | 30px (`--text-3xl`) | 600/700 | 1.2 |
| Section title | 18px (`--text-lg`) | 600 | 1.55 |
| Display | 48px (`--text-5xl`) | 700 | 1.17 |

---

## Copywriting Contract

No copy changes this phase (visual-only). Existing ru-RU strings stay. Reference for consistency:

| Element | Copy |
|---------|------|
| Primary CTA (task) | «Создать задачу» / «Экспорт» |
| Empty state heading | «Пока нет ячеек» |
| Empty state body | «Создайте первую ячейку, чтобы начать работу» |
| Error state | problem + «Повторить» retry |
| Destructive confirmation | «Отменить задачу»: «Это действие нельзя отменить» |

---

## Per-screen polish (visual pass — NO relayout; founder approved current layout)

Token-driven pass on the 5 routes / 6 surfaces. Per grill (2026-06-13): **palette + rhythm + 1–2
targeted density nudges** where a clear issue exists (e.g. an over-spread task-result header). Density
nudges use existing scale tokens only. Still **no relayout, no new sections, no new components.**
Any density nudge is captured per-screen in the table below and flagged in the execute-phase diff.

| Surface | File | Pass |
|---|---|---|
| Auth (login/register) | `features/auth/*`, `app/AuthShell.tsx` | New palette; footer/register link → `text-cta-hover`; CTA white text; focus ring blue |
| Cells list | `features/cells/CellsListPage.tsx` | Link cells `text-cta`→`text-cta-hover`; template Badge stays neutral; table header `bg-surface` rhythm |
| Cell detail | `features/cells/CellDetailPage.tsx` | Palette only; metadata card spacing |
| Task submit | `features/tasks/TaskSubmitPage.tsx` | Palette; role pills stay neutral; preset chip = secondary |
| Task result | `features/tasks/TaskResultPage.tsx` | Active tab indicator blue; in-content links `text-cta-hover`; artifact-card rhythm `--space-6`; success badge stays emerald |
| App shell | `app/AppLayout.tsx`, `components/ui/app-shell` | Sidebar active = `bg-surface` fill + `text-primary` (NOT blue fill); deepened surfaces |

**Link rule (corrected during execution):** accent-as-link moves `text-cta` → **`text-cta-hover`**
(NOT the static `text-brand-400` the draft suggested). A static `brand-400 #60a5fa` is great on dark
(7.4:1) but **fails light mode** (2.4:1 on white); `text-cta` fails *dark* (3.6:1). `text-cta-hover` is
theme-aware (`#60a5fa` dark / `#1e40af` light) → passes **both** modes. Relatedly, **primary button
hover** changed `bg-cta-hover` → **`bg-brand-700`** (darkens; keeps white text legible — a lighter
hover would drop white-on-button to 2.5:1). Both are values-only / names-stable.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | (already materialized in 00.7 — no new blocks) | not required |
| third-party | none | n/a |

No new components. Barrel stays exactly 18 exports (CI gate). `new-components-needed:` — **none**.

---

## Grill resolutions (2026-06-13 — all forks closed)

1. ~~`info` → cyan~~ — **CLOSED:** founder chose cyan `#06b6d4` (over slate-gray / accept-overlap).
2. ~~Per-screen polish depth~~ — **CLOSED:** palette + rhythm **+ 1–2 targeted density nudges** where a
   clear issue exists; no relayout / new screens / new components.
3. ~~Exact teamly hex~~ — CLOSED: founder locked `#2563eb` as the explicit value.
4. ~~Vivid vs muted~~ — CLOSED: Royal Blue chosen.

→ No open items. Ready for `/gsd:plan-phase 00.8`.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS (no change — existing ru-RU)
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS (palette + contrast table, recomputed by checker)
- [x] Dimension 4 Typography: PASS (unchanged)
- [x] Dimension 5 Spacing: PASS (unchanged scale)
- [x] Dimension 6 Registry Safety: PASS (no new components)

**Approval:** approved 2026-06-13 (gsd-ui-checker — 6/6 dimensions PASS)
