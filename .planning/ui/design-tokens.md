# Oriion Design Tokens — Nordic Warm

- **Version:** 0.1.0 (Wave 0)
- **Status:** temporary palette (final после OQ-09 Wave 2 brand refresh)
- **Source of truth:** this file (per DECISION-4, GRILL-DECISIONS-ORIION.md §5.1)
- **Materialization:** CSS variables в `frontend/src/styles/tokens.css` — Phase 00.7 deliverable. Здесь — spec only.

---

## 1. Philosophy

**Nordic Warm** — холодная база (slate) + единый тёплый акцент (amber). Дизайн-стратегия:

- **Dark-first:** target audience — developers + WB-Seller power-users работающие в вечерних/ночных сменах. OLED energy efficiency. Reduces eye strain.
- **Single accent:** amber-500 — единственный brand colour. Никаких "цветовых салатов" — info/warning разделены через iconography + semantic placement, а не через 5+ accent hues.
- **Anti-cold-blue:** обычные SaaS используют cold-blue (#3b82f6) как primary. Это вызывает ассоциации с "корпоративным холодом". Amber conveys reliability + warmth without aggression.
- **Structural stability:** scale / spacing / radius — структурные, остаются стабильны даже если Wave 2 brand refresh поменяет palette.

---

## 2. Colors

### 2.1 Base (neutral slate scale)

| Token | Hex | RGB | Tailwind ref | Usage |
|---|---|---|---|---|
| `--color-base-50`  | `#f8fafc` | `248 250 252` | slate-50  | Text emphasized on dark / bg primary on light |
| `--color-base-100` | `#f1f5f9` | `241 245 249` | slate-100 | Text on dark / bg elevated on light |
| `--color-base-200` | `#e2e8f0` | `226 232 240` | slate-200 | Border default on light |
| `--color-base-300` | `#cbd5e1` | `203 213 225` | slate-300 | Border emphasis on light / text muted on dark |
| `--color-base-400` | `#94a3b8` | `148 163 184` | slate-400 | Text tertiary / placeholder |
| `--color-base-500` | `#64748b` | `100 116 139` | slate-500 | Text secondary |
| `--color-base-600` | `#475569` | `71 85 105`   | slate-600 | Border emphasis on dark |
| `--color-base-700` | `#334155` | `51 65 85`    | slate-700 | Border default on dark |
| `--color-base-800` | `#1e293b` | `30 41 59`    | slate-800 | Surface elevated on dark |
| `--color-base-900` | `#0f172a` | `15 23 42`    | slate-900 | Bg primary on dark / text on light |
| `--color-base-950` | `#020617` | `2 6 23`      | slate-950 | Bg deepest on dark (modal backdrop) |

### 2.2 Brand / Primary (amber accent)

| Token | Hex | RGB | Tailwind ref | Usage |
|---|---|---|---|---|
| `--color-primary-100` | `#fef3c7` | `254 243 199` | amber-100 | Badge bg / primary surface |
| `--color-primary-400` | `#fbbf24` | `251 191 36`  | amber-400 | Primary disabled / muted |
| `--color-primary-500` | `#f59e0b` | `245 158 11`  | amber-500 | **Primary CTA / brand accent** |
| `--color-primary-600` | `#d97706` | `217 119 6`   | amber-600 | Primary hover |
| `--color-primary-700` | `#b45309` | `180 83 9`    | amber-700 | Primary active/pressed |

### 2.3 Semantic

| Token | Hex | RGB | Tailwind ref | Usage |
|---|---|---|---|---|
| `--color-success-100` | `#d1fae5` | `209 250 229` | emerald-100 | Success surface (toast bg) |
| `--color-success-500` | `#10b981` | `16 185 129`  | emerald-500 | Success text / icon |
| `--color-success-600` | `#059669` | `5 150 105`   | emerald-600 | Success hover/emphasis |
| `--color-warning-100` | `#fef3c7` | `254 243 199` | amber-100   | Warning surface (alias к primary) |
| `--color-warning-500` | `#f59e0b` | `245 158 11`  | amber-500   | Warning text / icon (alias к primary — single-accent system) |
| `--color-danger-100`  | `#ffe4e6` | `255 228 230` | rose-100    | Danger surface |
| `--color-danger-600`  | `#e11d48` | `225 29 72`   | rose-600    | **Danger text / destructive CTA** |
| `--color-danger-700`  | `#be123c` | `190 18 60`   | rose-700    | Danger hover |
| `--color-info-100`    | `#dbeafe` | `219 234 254` | blue-100    | Info surface |
| `--color-info-500`    | `#3b82f6` | `59 130 246`  | blue-500    | Info text / icon (neutral, не brand) |

### 2.4 Dark/Light mode mappings

**Default scheme:** `prefers-color-scheme: dark` OR `[data-theme="dark"]` selector.
**Toggle:** `[data-theme="light"]` overrides root.

| Semantic role | Dark mode | Light mode |
|---|---|---|
| `--bg-primary`     | `--color-base-900` (`#0f172a`) | `--color-base-50`  (`#f8fafc`) |
| `--bg-elevated`    | `--color-base-800` (`#1e293b`) | `--color-base-100` (`#f1f5f9`) |
| `--bg-overlay`     | `--color-base-950` (`#020617`) | `rgba(15,23,42,0.4)` |
| `--text-primary`   | `--color-base-50`  (`#f8fafc`) | `--color-base-900` (`#0f172a`) |
| `--text-secondary` | `--color-base-300` (`#cbd5e1`) | `--color-base-500` (`#64748b`) |
| `--text-tertiary`  | `--color-base-400` (`#94a3b8`) | `--color-base-400` (`#94a3b8`) |
| `--border-default` | `--color-base-700` (`#334155`) | `--color-base-200` (`#e2e8f0`) |
| `--border-emphasis`| `--color-base-600` (`#475569`) | `--color-base-300` (`#cbd5e1`) |
| `--cta-primary`    | `--color-primary-500`          | `--color-primary-600` |
| `--cta-primary-hover` | `--color-primary-400`        | `--color-primary-700` |

---

## 3. Typography

### 3.1 Font families

| Token | Value | Usage |
|---|---|---|
| `--font-sans` | `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif` | UI text (default) |
| `--font-mono` | `'JetBrains Mono', 'Cascadia Code', Consolas, 'Liberation Mono', monospace` | Code / structured data / IDs / hashes |

### 3.2 Type scale (Major Third 1.250 ratio, base 16px)

| Token | Size | Line-height | Usage |
|---|---|---|---|
| `--text-xs`   | `12px` | `16px` | Captions, helper text, badge labels |
| `--text-sm`   | `14px` | `20px` | Body small, table cells, form helper |
| `--text-base` | `16px` | `24px` | Body default |
| `--text-lg`   | `18px` | `28px` | Body emphasized, card titles |
| `--text-xl`   | `20px` | `28px` | Section subtitle |
| `--text-2xl`  | `24px` | `32px` | Page subtitle |
| `--text-3xl`  | `30px` | `36px` | Page title |
| `--text-4xl`  | `36px` | `40px` | Hero |
| `--text-5xl`  | `48px` | `56px` | Display (landing only) |

### 3.3 Font weights

| Token | Value | Usage |
|---|---|---|
| `--font-regular`  | `400` | Body text |
| `--font-medium`   | `500` | UI labels, buttons |
| `--font-semibold` | `600` | Titles, emphasized text |
| `--font-bold`     | `700` | Hero, display |

### 3.4 Letter spacing

| Token | Value | Usage |
|---|---|---|
| `--tracking-tight`  | `-0.025em` | Hero / display |
| `--tracking-normal` | `0`        | Body / UI default |
| `--tracking-wide`   | `0.025em`  | All-caps badges, eyebrow labels |

---

## 4. Spacing scale (4px base)

| Token | Value | Common usage |
|---|---|---|
| `--space-0`  | `0`    | reset |
| `--space-1`  | `4px`  | icon-text gap, tight inline |
| `--space-2`  | `8px`  | form field internal padding, small gap |
| `--space-3`  | `12px` | input vertical padding, badge padding |
| `--space-4`  | `16px` | card padding small, default gap |
| `--space-5`  | `20px` | card padding medium |
| `--space-6`  | `24px` | card padding large, section gap small |
| `--space-8`  | `32px` | section gap default |
| `--space-10` | `40px` | section gap medium |
| `--space-12` | `48px` | section gap large |
| `--space-16` | `64px` | hero block padding |
| `--space-20` | `80px` | page-level vertical rhythm |

---

## 5. Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-none` | `0`      | Tables, full-bleed surfaces |
| `--radius-sm`   | `4px`    | Inputs, small badges |
| `--radius-md`   | `8px`    | Buttons (default), small cards |
| `--radius-lg`   | `12px`   | Cards, modals |
| `--radius-xl`   | `16px`   | Hero cards, landing surfaces |
| `--radius-full` | `9999px` | Avatars, pill badges, circular buttons |

---

## 6. Shadow

| Token | Value | Usage |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(15, 23, 42, 0.08)` | Hover lift on cards |
| `--shadow-md` | `0 4px 6px rgba(15, 23, 42, 0.10), 0 2px 4px rgba(15, 23, 42, 0.06)` | Dropdowns, popovers |
| `--shadow-lg` | `0 10px 15px rgba(15, 23, 42, 0.12), 0 4px 6px rgba(15, 23, 42, 0.08)` | Modals, drawers |
| `--shadow-xl` | `0 20px 25px rgba(15, 23, 42, 0.14), 0 10px 10px rgba(15, 23, 42, 0.10)` | High-elevation overlays |
| `--shadow-focus-ring` | `0 0 0 3px rgba(245, 158, 11, 0.40)` | **Focus indicator (amber-500 alpha 40%)** |

---

## 7. Motion

### 7.1 Durations

| Token | Value | Usage |
|---|---|---|
| `--duration-fast`    | `150ms` | Hover, focus, micro-interactions |
| `--duration-normal`  | `250ms` | Modal / drawer transitions |
| `--duration-slow`    | `400ms` | Page transitions |
| `--duration-deliberate` | `600ms` | Onboarding, celebratory moments |

### 7.2 Easings

| Token | Value | Usage |
|---|---|---|
| `--easing-default`     | `cubic-bezier(0.4, 0, 0.2, 1)` | Material-standard (most transitions) |
| `--easing-emphasized`  | `cubic-bezier(0.2, 0, 0, 1)`   | Material-emphasized (entrances) |
| `--easing-decelerate`  | `cubic-bezier(0, 0, 0.2, 1)`   | Incoming (modal open) |
| `--easing-accelerate`  | `cubic-bezier(0.4, 0, 1, 1)`   | Outgoing (modal close) |

### 7.3 Reduced motion
Respect `prefers-reduced-motion: reduce` — disable non-essential transitions, keep only opacity fades ≤ 150ms.

---

## 8. Breakpoints

| Token | Min-width | Target |
|---|---|---|
| `sm`  | `640px`  | Mobile landscape |
| `md`  | `768px`  | Tablet |
| `lg`  | `1024px` | Laptop |
| `xl`  | `1280px` | Desktop |
| `2xl` | `1536px` | Wide desktop |

Mobile-first: styles default к < sm, then progressively enhance.

---

## 9. Z-index scale

| Token | Value | Usage |
|---|---|---|
| `--z-base`     | `0`  | Default flow |
| `--z-dropdown` | `10` | Select menus, autocomplete |
| `--z-sticky`   | `20` | Sticky headers/footers |
| `--z-overlay`  | `30` | Drawer scrim, drawer backdrop |
| `--z-modal`    | `40` | Modals, dialogs |
| `--z-popover`  | `50` | Popovers, context menus |
| `--z-toast`    | `60` | Toast notifications |
| `--z-tooltip`  | `70` | Tooltips (always topmost) |

---

## 10. Usage guidance

### 10.1 When to use `primary-500` vs `primary-600`

- `primary-500` (amber-500) — default brand surface (CTA, link, badge). В dark mode это actionable default.
- `primary-600` (amber-600) — hover/pressed state в light mode (default — dark mode так что hover = `primary-400`, lighter).
- `primary-400` — disabled / muted brand surface, и hover state в dark mode.

### 10.2 Single-accent philosophy

В Oriion **только amber** служит "цветным" акцентом. Semantic colours (success-emerald, danger-rose, info-blue) used **только** для semantic feedback:

- Success/error toasts
- Form validation states
- Status badges (active/inactive/error)
- Destructive button variant

Никогда не используй emerald/rose/blue для decoration, navigation highlights, или brand surfaces. Это сохраняет visual hierarchy: amber = "this is Oriion", semantic = "this is feedback".

### 10.3 Dark-first reasoning

- Target audience: developers, AI-team operators, WB-Seller power-users.
- Use cases include evening/night shifts (WB analytics check before bed, agent oversight в нерабочие часы).
- OLED-friendly: `--bg-primary` = `#0f172a` (~5% luminance) экономит battery on AMOLED laptops/phones.
- Light mode supported but optional — toggle через user preference (saved per ADR-001 user settings).

### 10.4 Future evolution (Wave 2)

- Brand palette (amber → possibly Oriion-orange) может измениться post-OQ-09 resolution.
- **Structural tokens stay** — spacing, radius, type scale, shadow recipes — не меняются.
- Semantic mappings (`--bg-primary`, `--text-primary`) могут перенаправляться на новые brand tokens без необходимости touch every component.

---

## 11. References

- **DECISION-4** — Nordic Warm palette source: `.planning/decisions/ADR-028-policies-registry.md` §5.1
- **ADR-001** — Frontend stack (Vite + React 19 + TanStack + shadcn + Tailwind v4)
- **ADR-026** — Vertical expertise (UI surface across verticals must share design language)
- **OQ-09** — Brand identity unresolved (Wave 2 — final palette TBD)
- **Phase 00.7 deliverable** — CSS variables materialization → `frontend/src/styles/tokens.css`
- **Phase 00.7 deliverable** — Tailwind v4 theme config → `frontend/tailwind.config.ts`

---

## 12. Change log

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-13 | Initial Wave 0 foundation (Nordic Warm). Generated per DECISION-4. |
