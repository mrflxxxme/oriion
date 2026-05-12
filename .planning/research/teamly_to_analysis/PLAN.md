# Plan: teamly.to Analysis & Mapping

> **Цель:** Создать пользовательскую (UX/UJ) и архитектурную (technical) карты teamly.to с уровнем детализации, достаточным для воспроизведения функционала в нашем продукте. Не plagiarize, а понять design choices + найти design gaps + сверить с нашим планом из roadmap.

## Output structure

`.planning/research/teamly_to_analysis/`:

| File | Содержимое |
|---|---|
| `PLAN.md` | этот файл — план и status |
| `00-overview.md` | что такое teamly.to, positioning, целевая аудитория, бизнес-модель, pricing-страница |
| `01-user-journeys.md` | все UX flows step-by-step: registration → onboarding → создание team → постановка задачи → результат → billing |
| `02-architecture-frontend.md` | frontend stack, framework, bundle analysis, ключевые компоненты, state management, routing |
| `03-architecture-backend.md` | API endpoints, request/response schemas, auth flow, headers, WebSocket connections |
| `04-pixel-department.md` | детальный анализ Pixel UI: технология (canvas/SVG/WebGL/PixiJS/Phaser?), сцена, анимации, sync с backend |
| `05-agent-system.md` | как агенты работают: создание, конфигурация, исполнение задач, какие models, как стримятся ответы |
| `06-billing-model.md` | Teamly Dollars, tariffs, payment integration, lifecycle |
| `07-integrations.md` | какие 3rd-party tools поддерживаются |
| `08-marketing-content.md` | landing pages, копи, кейсы, отзывы — для нашего content marketing reference |
| `screenshots/` | скриншоты ключевых экранов (нумеровать `01-step.png`, `02-step.png`...) |
| `network-traces/` | HAR-like JSON captures of key flows |
| `RECONSTRUCTION-NOTES.md` | финальный документ: gap analysis vs наш план, что копируем, что НЕ копируем, риски |
| `STATUS.md` | живой статус: что сделано, что pending |

## Method

### Tools

- **mcp__Claude_in_Chrome__\*** — primary toolset:
  - `list_connected_browsers` — проверить connectivity
  - `navigate` — переход по URL
  - `read_page` / `get_page_text` — содержимое страницы
  - `read_network_requests` — захват API-calls
  - `read_console_messages` — JS errors / debug
  - `javascript_tool` — custom DOM/state inspection
  - `find` + `form_input` + `computer` (click) — навигация по UX
  - `tabs_create_mcp` / `tabs_close_mcp` / `tabs_context_mcp` — multi-tab work
- **WebFetch** — для статичных pages (fallback если Chrome MCP недоступен)
- **WebSearch** — context о компании, обзоры, отзывы

### Methodology

1. **Read-only first:** не регистрируемся, не вводим креды, не нагружаем. Marketing pages + публично доступное.
2. **Network sniffing для API surface:** при public navigation смотрим, какие endpoints вызываются (даже без auth — open API часть видна).
3. **DOM inspection через javascript_tool:** ищем React-deeptree, frameworks, library-fingerprints.
4. **Screenshot per step:** для последующего sharing команде.
5. **Authenticated exploration (опц.):** только если у пользователя есть тестовый аккаунт teamly.to и он согласен с риском ToS-нарушения.

## Phase breakdown

### Этап 1 — Discovery & marketing (~15 мин)

**Delegated to:** general-purpose agent (с MCP Chrome)

Steps:
1. `list_connected_browsers` → проверить, что MCP Chrome работает
2. `navigate` к `https://teamly.to/`
3. Read marketing copy → сохранить в `00-overview.md`
4. `read_network_requests` для homepage → identify CDN, analytics, tracking
5. `javascript_tool`: extract `window.*` fingerprints, framework signatures (React DevTools, etc.)
6. Скриншот homepage, How-it-works, Pricing
7. Bundle inspection: какие JS-чанки загружаются, paths, hash patterns → guess framework (Next.js? Vite?)

**Output:** `00-overview.md`, `02-architecture-frontend.md` (initial), 5–10 screenshots

### Этап 2 — Public-facing pages deep dive (~20 мин)

**Delegated to:** general-purpose agent (с MCP Chrome)

Steps:
1. Все pages в навигации: How it works, Pricing, Privacy, Terms, Cookie Policy, Licenses, Log in (страница, не действие)
2. Find "Get Started" flow — где приземляются (signup form? OAuth?)
3. Read landing UI components — Pixel-стиль (если есть на landing)
4. Static asset analysis: images, fonts, SVG/PNG/Sprite
5. SEO-meta: tags, OG, descriptions
6. Sitemap.xml / robots.txt → дополнительные pages

**Output:** `08-marketing-content.md`, расширение `02-architecture-frontend.md`

### Этап 3 — Authentication & onboarding (опц., ~25 мин)

**Условие:** пользователь имеет тестовый teamly.to аккаунт ИЛИ соглашается зарегистрировать одноразовый

**Delegated to:** general-purpose agent (с MCP Chrome) + supervision пользователя

Steps:
1. Если есть аккаунт — login flow с network capture
2. Onboarding step-by-step с screenshot per step
3. Network requests: auth endpoints, JWT/session-cookie analysis
4. WebSocket connections: какие, к каким endpoints

**Output:** `01-user-journeys.md`, network-traces JSON, screenshots

### Этап 4 — Pixel Department deep-dive (~20 мин)

**Delegated to:** general-purpose agent (с js_tool, specialized prompt)

Steps:
1. Inspect Pixel UI page DOM/canvas
2. Identify rendering tech: PixiJS / Phaser / Three.js / custom canvas / SVG?
3. Look at sprite sheets / asset URLs
4. WebSocket message format для sync с backend
5. Animation logic: где живёт state — frontend, backend, или synchronized
6. Performance characteristics (frame rate, etc.)

**Output:** `04-pixel-department.md` с deep detail

### Этап 5 — Agent system & runtime (~25 мин)

**Delegated to:** general-purpose agent (с js_tool, network)

Steps:
1. При создании task в UI — захват API-калла
2. Streaming response analysis (SSE? WebSocket? long-poll?)
3. Tool calls visibility — какие tools предоставлены агентам
4. Model identification (если visible в payload или ответе)
5. Cost/billing tracking на UI level

**Output:** `05-agent-system.md`, `06-billing-model.md`, `07-integrations.md`

### Этап 6 — Reconstruction notes & gap analysis (~15 мин)

**Delegated to:** general-purpose agent (synthesis)

Steps:
1. Compile all findings
2. Compare с нашим roadmap'ом — где совпадаем, где расходимся
3. Список «что у них хорошо, нам взять» (UX patterns, copy, flow ideas)
4. Список «что у них плохо/не для РФ» (что НЕ копируем)
5. Список новых рисков, открытых анализом

**Output:** `RECONSTRUCTION-NOTES.md`

## Delegation matrix

| Phase | Agent | Tools needed | Estimated time |
|---|---|---|---|
| 1 — Discovery | general-purpose | Chrome MCP (navigate, read_page, network, js_tool), WebSearch | 15 мин |
| 2 — Marketing | general-purpose | Chrome MCP, WebFetch | 20 мин |
| 3 — Auth/Onboarding (опц.) | general-purpose | Chrome MCP (full), supervision | 25 мин |
| 4 — Pixel Department | general-purpose | Chrome MCP (js_tool focus) | 20 мин |
| 5 — Agent system | general-purpose | Chrome MCP (network focus) | 25 мин |
| 6 — Reconstruction | general-purpose | Read tool | 15 мин |

**Total:** ~2 часа AI-agent time + супервайзерская проверка ключевых артефактов.

## Prerequisites (требуют ответа пользователя)

| # | Вопрос | Действие при «нет» |
|---|---|---|
| Q1 | Установлен ли Claude Chrome extension и есть ли connected browser? | Fallback: WebFetch + WebSearch only — менее богатый результат |
| Q2 | Есть ли у вас тестовый аккаунт teamly.to для Этапа 3? | Этап 3 пропускаем, ограничиваемся public-pages |
| Q3 | Согласны ли с риском ToS-нарушения (teamly.to может запрещать automated access)? | При «нет» — manual-only, Chrome MCP в режиме semi-manual (вы кликаете, мы capture) |
| Q4 | Готовы поделиться payment data для проверки billing-flow до конца? | Опц., Этап 5 без actual payment |

## Risks during execution

| Risk | Mitigation |
|---|---|
| Bot detection / blocking | Slow pace, human-like timing, real Chrome (не headless) |
| ToS violation | Только read-only, не реверс-инжиниринг JS-кода, не модификация UI |
| Cloudflare challenge | Manual fallback — пользователь делает action, мы capture |
| JS app не рендерится в DOM сразу | Wait + retry, use `read_page` после задержки |
| Anti-scraping captcha | Manual fallback |

## Acceptance criteria

- [ ] Все 10 файлов в `.planning/research/teamly_to_analysis/` заполнены
- [ ] ≥30 screenshots ключевых экранов
- [ ] ≥5 network-traces JSON-капсул
- [ ] RECONSTRUCTION-NOTES.md содержит gap analysis vs нашего roadmap'а
- [ ] Все архитектурные insights связаны с конкретными ADR (если требуется обновление)
- [ ] Risk register обновлён, если открыты новые риски

## Status

См. `STATUS.md` (создаётся при старте выполнения).
