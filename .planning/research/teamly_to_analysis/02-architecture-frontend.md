# 02 — Architecture: Frontend

## Stack identified

| Слой | Технология | Доказательство |
|---|---|---|
| Framework | **Next.js 15 (App Router)** + Turbopack | `/_next/static/chunks/turbopack-*.js`, `framework.next: true` |
| Language | TypeScript (предположительно — стандарт Next.js) | (минификация скрыла) |
| Bundler | Turbopack (Rust-based, Next.js 15) | chunk-имена `turbopack-*.js` |
| Auth | **Clerk** v5.125.10 (clerk-js) | `clerk.teamly.to/npm/@clerk/clerk-js@5.125.10/dist/*` |
| Fonts | Geist + Geist Mono + **Press Start 2P** | `body.className = "geist_*-module ... press_start_2p_*-module"` |
| 2D rendering | Native HTML `<canvas>` 2D API | 45 canvases, `getContext('2d')`, no PIXI/Phaser/Three |
| Animation | CSS `@keyframes` + canvas redraw | `pixelBob` keyframe, `transition-opacity` class |
| Error tracking | **Sentry** v10.47.0 (next.js SDK) | `o4511183472427008.ingest.de.sentry.io/api/.../envelope/?sentry_client=sentry.javascript.nextjs%2F10.47.0` |
| Analytics | Google Tag Manager + GA4 (`G-XD4VEK4S6N`) | gtag/gtm scripts + GA4 collect endpoint |
| Auto-translate | Google Translate widget (visible на Ru-Chrome) | translate.googleapis.com requests |

## Bundle architecture

Loaded chunks (Next.js 15 App Router pattern):
- 25 chunks in `/_next/static/chunks/<hash>.js`
- chunks named via content-hash (immutable)
- One Turbopack runtime chunk
- Lazy-loaded: Clerk UI subchunks loaded only when needed (`framework_clerk`, `vendors_clerk`, `ui-common_clerk`, `subscriptionDetails_clerk`)

Bundle размеры не измерены, но число chunks указывает на code-splitting per-route.

## CSS framework

Multiple CSS layers (`@layer theme {}`, `@layer utilities {}`):
- **Tailwind** (вероятно v4 — судя по `@container` queries and `@layer utilities`)
- Custom design tokens: `--font-sans`, `--font-mono`, `--font-pixel`
- Custom animation: `@keyframes pixelBob { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-2px); } }`
- Class naming: `geist_a71539c9-module__T19VSG__variable` — CSS-modules + Turbopack hash

## Visual system (Pixel Art)

См. полный разбор в `04-pixel-department.md`. Кратко:
- Каждый agent-avatar — `<canvas width=2× height=2×>` styled `width=N height=N` (retina-rendering)
- Sprite source: PNG-sheets at `/api/assets/agents/<id>/<state>.png`
- CSS `pixelBob` keyframe для idle bounce
- Press Start 2P font для всех headings + buttons (retro pixel-art typography)
- `pointer-events-none select-none` classes — canvas-elements не интерактивны (interactions через надлежащие button-wrappers)

## State management

Не идентифицирован явный store (Redux/Zustand/Jotai) — кода обфусцирован. Учитывая Next.js 15 App Router + Clerk auth, скорее всего:
- React Server Components для статичных частей
- Client-side state через React hooks
- Server state через native fetch (React Query / TanStack возможен, но не подтверждён)

## Internationalization (i18n)

- Native locale: **English** (en-US).
- Russian текст в скриншотах — это **Chrome auto-translate** (Google Translate widget, не Teamly i18n).
- Title page изменилась: "Teamly - Your AI Agents..." → "Teamly — ваши ИИ-агенты, управляемые в облаке."
- Признаков встроенной i18n не найдено.

## Performance characteristics

- 60 FPS — не измерялось, но 45 canvases + pixelBob keyframes одновременно работают без visible jank.
- Service Worker — присутствует (`navigator.serviceWorker`).
- Каждый sprite PNG → **13.5 MB** (`formal01-writing/idle.png`) — крупные ассеты, кешируются 1 год (`max-age=31536000, immutable`).
- Cookies: `__client_uat`, `__client_uat_u9GWt4tD`, `clerk_active_context`, `__session`, `__session_u9GWt4tD` — все Clerk.
- localStorage:
  - `__clerk_environment` (Clerk config)
  - `teamly_analytics_consent_v1` (cookie consent)
  - `dev-nav-open` (sidebar state)
  - `teamly_tour_seen` (onboarding tracked)
  - `teamly-incident-banner-2026-05-08` (incident banner dismissal, today's date)

## SEO/Meta

- `<meta name="description">`: "Managed hosting for AI agents. Zero infrastructure. Full control. Watch your AI team work in real-time through the Pixel Department."
- `<title>`: "Teamly - Your AI Agents, Managed in the Cloud"
- Favicon set (16, 32, 192 px likely)
- OG-image not inspected

## Accessibility

- Pixel-art canvases имеют `pointer-events-none` — focus идёт на проперd wrapper.
- ARIA — не специфически измерено, no obvious deficiencies в read_page output.
- Reading order вокруг ASCII-style headings (типа `PRICING`, `HOW IT WORKS`) выглядит OK.

## DevTools fingerprinting

- React-marker элементы (`#__next`) — не обнаружен в текущем DOM (Next.js 15 App Router использует другую структуру).
- React DevTools detection: false (`framework.react: false`) — но это false-negative, App Router не оставляет `data-reactroot`.

## Frontend security headers (не captured, но стоит проверить в полном HAR)

Подразумевается:
- CSP (включая connect-src для Clerk, Sentry, Composio, OAuth provider)
- HSTS
- Strict CORS на /api/* (наблюдалось `credentials: 'include'`)

## Что мы НЕ нашли

- Service Worker logic (не открывали /sw.js)
- PWA manifest (наверняка есть, но не извлекли)
- Storybook / design system (закрыта)
- Custom Elements / Web Components
