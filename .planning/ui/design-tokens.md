# Oriion Design Tokens — Professional cool-blue

- **Version:** 0.2.0 (Wave 0)
- **Status:** temporary palette (final после OQ-09 Wave 2 brand refresh). **v0.2.0 restyling выполнен в [Phase 00.8](../roadmap/wave-0-foundation/phases/00.8-design-restyling.md)** per [ADR-031 (Accepted)](../decisions/ADR-031-design-direction-restyling.md): глубокая прохладная professional-dark палитра + Royal-Blue акцент (`#2563eb`, выбран на bake-off 2026-06-13). Изменены только значения; имена/структура токенов стабильны. Контракт: [UI-SPEC-00.8.md](./UI-SPEC-00.8.md).
- **Source of truth:** this file (per DECISION-4 — see [ADR-028](../decisions/ADR-028-policies-registry.md#decision-4))
- **Materialization:** CSS variables в `frontend/src/styles/tokens.css` — Phase 00.7 deliverable. Здесь — spec only.

---

## 1. Philosophy

**Professional cool-blue (v0.2.0)** — глубокая прохладная slate-база + единый Royal-Blue акцент. Дизайн-стратегия (per ADR-031, founder bake-off 2026-06-13):

- **Dark-first:** target audience — developers + WB-Seller power-users работающие в вечерних/ночных сменах. OLED energy efficiency. Reduces eye strain. Канва углублена (`bg-page` `#0f172a`→`#0b111e`) для «взрослого» professional-dark вида в духе Claude Code.
- **Single accent:** Royal Blue `#2563eb` — единственный brand colour. Никаких "цветовых салатов" — feedback (success/warning/danger/info) разделён через iconography + semantic placement, а не через 5+ accent hues. Акцент только на: CTA, active-tab, ссылки (через `cta-hover`-стоп), focus-ring, `Badge primary`.
- **Blue on dark — две роли акцента:** насыщенный `#2563eb` как фон CTA требует **белого** текста (5.17:1); как текст ссылки на тёмном он слишком тёмен (3.6:1), поэтому ссылки берут более светлый/прохладный стоп через `--cta-primary-hover` (dark `#60a5fa` 7.4:1 / light `#1e40af` ~9:1). Hover CTA **темнеет** (`brand-700`), а не светлеет — чтобы белый текст оставался читаемым.
- **info ≠ brand:** семантический `info` переведён на **cyan** (`#06b6d4`), чтобы синий бренд оставался единственным «брендовым синим». `warning` (amber) теперь самостоятельная семантика, а не алиас бренда.
- **Structural stability:** scale / spacing / radius / type — структурные, остаются стабильны даже если Wave 2 brand refresh поменяет palette.

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
| `--color-base-600` | `#37445f` | `55 68 95`    | deepened (v0.2) | Border emphasis on dark / text-secondary on light |
| `--color-base-700` | `#26324a` | `38 50 74`    | deepened (v0.2) | Border default on dark |
| `--color-base-800` | `#141c2b` | `20 28 43`    | deepened (v0.2) | Surface elevated on dark |
| `--color-base-900` | `#0b111e` | `11 17 30`    | deepened (v0.2) | Bg primary on dark / text on light |
| `--color-base-950` | `#060a13` | `6 10 19`     | deepened (v0.2) | Bg deepest on dark (modal backdrop) |

### 2.2 Brand / Primary (Royal Blue accent)

| Token | Hex | RGB | Tailwind ref | Usage |
|---|---|---|---|---|
| `--color-primary-100` | `#dbeafe` | `219 234 254` | blue-100 | Badge bg / primary surface (light chip) |
| `--color-primary-400` | `#60a5fa` | `96 165 250`  | blue-400 | **Links on dark** (via `cta-hover`) / dark-mode CTA hover-target / muted |
| `--color-primary-500` | `#2563eb` | `37 99 235`   | blue-600 | **Primary CTA / brand accent** (white text) |
| `--color-primary-600` | `#1d4ed8` | `29 78 216`   | blue-700 | Light-mode CTA / dark pressed |
| `--color-primary-700` | `#1e40af` | `30 64 175`   | blue-800 | Active/pressed / CTA hover-darken / link-on-light |

### 2.3 Semantic

| Token | Hex | RGB | Tailwind ref | Usage |
|---|---|---|---|---|
| `--color-success-100` | `#d1fae5` | `209 250 229` | emerald-100 | Success surface (toast bg) |
| `--color-success-500` | `#10b981` | `16 185 129`  | emerald-500 | Success text / icon |
| `--color-success-600` | `#059669` | `5 150 105`   | emerald-600 | Success hover/emphasis |
| `--color-warning-100` | `#fef3c7` | `254 243 199` | amber-100   | Warning surface (standalone v0.2 — больше не алиас бренда) |
| `--color-warning-500` | `#f59e0b` | `245 158 11`  | amber-500   | Warning text / icon (independent semantic — бренд теперь синий) |
| `--color-danger-100`  | `#ffe4e6` | `255 228 230` | rose-100    | Danger surface |
| `--color-danger-600`  | `#e11d48` | `225 29 72`   | rose-600    | **Danger text / destructive CTA** |
| `--color-danger-700`  | `#be123c` | `190 18 60`   | rose-700    | Danger hover |
| `--color-info-100`    | `#cffafe` | `207 250 254` | cyan-100    | Info surface (v0.2 — cyan, distinct from brand blue) |
| `--color-info-500`    | `#06b6d4` | `6 182 212`   | cyan-500    | Info text / icon (cyan — anti-collision с brand) |

### 2.4 Dark/Light mode mappings

**Default scheme:** `prefers-color-scheme: dark` OR `[data-theme="dark"]` selector.
**Toggle:** `[data-theme="light"]` overrides root.

> Names match the materialized `themes.css` (`--bg-page`/`--bg-surface`, post-00.7).

| Semantic role | Dark mode | Light mode |
|---|---|---|
| `--bg-page`        | `--color-base-900` (`#0b111e`) | `--color-base-50`  (`#f8fafc`) |
| `--bg-surface`     | `--color-base-800` (`#141c2b`) | `--color-base-100` (`#f1f5f9`) |
| `--bg-overlay`     | `--color-base-950` (`#060a13`) | `rgba(11,17,30,0.4)` |
| `--text-primary`   | `--color-base-50`  (`#f8fafc`) | `--color-base-900` (`#0b111e`) |
| `--text-secondary` | `--color-base-300` (`#cbd5e1`) | `--color-base-600` (`#37445f`) |
| `--text-tertiary`  | `--color-base-400` (`#94a3b8`) | `--color-base-500` (`#64748b`) |
| `--border-default` | `--color-base-700` (`#26324a`) | `--color-base-200` (`#e2e8f0`) |
| `--border-emphasis`| `--color-base-600` (`#37445f`) | `--color-base-300` (`#cbd5e1`) |
| `--cta-primary`    | `--color-primary-500` (`#2563eb`) | `--color-primary-600` (`#1d4ed8`) |
| `--cta-primary-hover` | `--color-primary-400` (`#60a5fa`) | `--color-primary-700` (`#1e40af`) |
| `--color-on-cta`   | `#ffffff` (mode-invariant)     | `#ffffff` |

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
| `--shadow-focus-ring` | `0 0 0 3px rgba(37, 99, 235, 0.40)` | **Focus indicator (Royal Blue / primary-500 alpha 40%)** |

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

### 10.1 Blue accent — how the stops map (v0.2)

Royal Blue (`#2563eb`) насыщен/тёмен, поэтому ведёт себя не как amber: «фон CTA» и «текст ссылки» берут **разные** стопы.

- **CTA фон** = `--cta-primary` → `primary-500` (`#2563eb`) dark / `primary-600` (`#1d4ed8`) light. Текст на CTA — **белый** (`--color-on-cta`), 5.17:1 / 6.70:1.
- **CTA hover** = темнее, не светлее: `bg-brand-700` (`#1e40af`), чтобы белый текст оставался читаемым (9.7:1). (НЕ `cta-hover`, иначе hover светлеет и белый проваливает AA.)
- **Ссылки / accent-as-text на поверхности** = `--cta-primary-hover` (`text-cta-hover`) → `primary-400` (`#60a5fa`) dark (7.4:1) / `primary-700` (`#1e40af`) light (~9:1). Mode-aware: светлый синий на тёмном, тёмный синий на светлом.
- `primary-100` (`#dbeafe`) — `Badge primary` фон (светлый чип) с текстом `brand-700`.

### 10.2 Single-accent philosophy

В Oriion **только Royal Blue** служит brand-акцентом. Semantic colours (success-emerald, warning-amber, danger-rose, info-cyan) used **только** для semantic feedback:

- Success/error toasts
- Form validation states
- Status badges (active/inactive/error)
- Destructive button variant

Никогда не используй emerald/amber/rose/cyan для decoration, navigation highlights, или brand surfaces. Это сохраняет visual hierarchy: Royal Blue = "this is Oriion", semantic = "this is feedback". info=cyan специально отделён от brand-blue.

### 10.3 Dark-first reasoning

> Обоснование пересмотрено 2026-07-15: прежняя формулировка опиралась на «WB-Seller power-users» — сегмент **удалён целиком** решением D-06 (вертикаль, коннектор, герой, пресет, golden). Аудитория ниже — фактическая для W2 (горизонталь `productivity-core` + `agency_marketing_ru` + `telegram_creator`).

- Target audience: SMB-операторы и personal-пользователи AI-команд, маркетинговые агентства, TG-креаторы; developers/AI-team operators.
- Use cases include evening/night shifts (контент-подготовка и agent oversight в нерабочие часы).
- OLED-friendly: `--bg-primary` = `#0f172a` (~5% luminance) экономит battery on AMOLED laptops/phones.
- Light mode supported but optional — toggle через user preference (saved per ADR-001 user settings).

### 10.4 Evolution — что гарантируется, а что нет (Wave 2)

> **Переписано 2026-07-15** (grill D-30). Прежняя формулировка обещала «**structural tokens stay** — spacing, radius, type scale, shadow recipes — не меняются» и тем самым **запрещала** ось `data-skin` из [D-20](../_session-context/DECISIONS-LOG.md), которую требуют спеки 02.1-retro / 02.2 / 02.6. Два контракта противоречили друг другу: агент, читающий этот файл, получал не тот ответ, что агент, читающий спеку фазы. Литералы в `frontend/src/styles/index.css` — материализация именно этого обещания, а не отдельный баг. См. [WAVE-1-RETRO.md §B](../WAVE-1-RETRO.md).

**Гарантируется — имена и структура, НЕ значения.** Это и был исходный интент (см. последний булит: «без необходимости touch every component»); прочтение «значения никогда не меняются» было побочным и ошибочным.

- **Имена/структура токенов стабильны:** набор `--radius-*` / `--text-*` / `--space-*` / `--font-*` и их семантические маппинги (`--bg-page`, `--text-primary`, …) — контракт для компонентов. Компоненты потребляют **семантические токены**, никогда — сырые значения.
- **Значения варьируются по осям.** Осей две, ортогональных:
  - `data-theme` — `light` / `dark` (существует с v0.2);
  - `data-skin` — опциональный скин-режим (D-20), **вводится в 02.6 поверх DS v0.3**; варьирует радиусы/шрифты/акценты.
  - Матрица `theme × skin` целиком обязана держать **WCAG AA**, не только дефолтная комбинация.
- **Механика:** каждый themeable-токен в `@theme` разрешается через `var()`. Литералы запрещены — грep-гейт стоит в AC 02.2, субстрат готовится в 02.1-retro.
- **Ось скина ≠ эстетика скина.** Этот файл фиксирует, что ось *разрешима*; чем она наполнена — решает редизайн (02.2, [ADR-042](../decisions/ADR-042-wave2-tier1-redesign.md)) и 02.6.
- Palette v0.3 определяется на bake-off внутри 02.2. Бренд **«Профики»** зафиксирован (OQ-09 закрыт 2026-07-10) — ребрендинг имени/лого вне скоупа.

---

## 11. References

- **DECISION-4** — Nordic Warm palette source: `.planning/decisions/ADR-028-policies-registry.md` §5.1
- **ADR-001** — Frontend stack (Vite + React 19 + TanStack + shadcn + Tailwind v4)
- **ADR-026** — Vertical expertise (UI surface across verticals must share design language)
- **OQ-09** — Brand identity **RESOLVED 2026-07-10**: бренд «Профики» / профики.online (`oriion` — только внутренний коднейм). Palette v0.3 — bake-off внутри 02.2, не блокируется брендом.
- **ADR-042** — Wave-2 tier-1 редизайн (DS v0.3): направление и bake-off
- **Phase 00.7 deliverable** — CSS variables materialization → `frontend/src/styles/tokens.css`
- **Phase 00.7 deliverable** — Tailwind v4 theme config → `frontend/tailwind.config.ts`

---

## 12. Change log

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-13 | Initial Wave 0 foundation (Nordic Warm). Generated per DECISION-4. |
| 0.1.0+note | 2026-06-11 | Forward-note: v0.2.0 restyling запланирован в Phase 00.8 (professional nordic, accent TBD) per ADR-031. Значения не менялись. |
| **0.2.0** | **2026-06-13** | **Phase 00.8 restyle (ADR-031 Accepted).** Amber accent → **Royal Blue `#2563eb`** (white CTA text; links via `cta-hover` stop; hover darkens to `brand-700`). Cool-slate canvas deepened (`base-600..950`). `info` blue→**cyan** (anti-collision); `warning`-amber now standalone semantic. `on-cta`→white; focus-ring→blue. Names/structure unchanged — values only. WCAG-AA table in [UI-SPEC-00.8.md](./UI-SPEC-00.8.md). |
