# STATUS — Teamly.to Analysis Session

> Session timestamp: 2026-05-12 (start, autonomous mode)

## Session summary

Authenticated session с user-аккаунтом КИРИЛЛ У. (uklonskiy.k@gmail.com, Free / No Plan). Полное прохождение Coordinator wizard, обход всех Settings tabs, capture catalog/api endpoints, paywall trigger.

## Документы готовы (10 files)

- [x] `PLAN.md` — план анализа (создан перед стартом)
- [x] `00-overview.md` — позиционирование, pricing, ЦА, ключевые claim'ы
- [x] `01-user-journeys.md` — все UX flows (Discovery, Wizard, Onboarding, Paywall, Settings)
- [x] `02-architecture-frontend.md` — Next.js 15 / Clerk / Canvas 2D / Sentry / GA4
- [x] `03-architecture-backend.md` — Cell concept, API endpoints, Composio integration
- [x] `04-pixel-department.md` — canvas-based rendering, sprite system, animations
- [x] `05-agent-system.md` — 13 team presets, agents catalog, autonomous mode, PARA
- [x] `06-billing-model.md` — Teamly Dollars, 4 tariffs, Polar, BYOK -80%
- [x] `07-integrations.md` — Composio 11 toolkits, 9 BYOK providers, Channels
- [x] `08-marketing-content.md` — copy, voice, value-stack, positioning
- [x] `RECONSTRUCTION-NOTES.md` — gap analysis vs наш roadmap + actionable updates
- [x] `STATUS.md` — этот файл

## Screenshots captured

| Скриншот | URL | Описание |
|---|---|---|
| ss_47807349x | / | Landing с Coordinator-input |
| ss_2892fgx17 | /#how-it-works | How it works section |
| ss_8173yj91l | /#pricing (scrolled) | 3-tariff card view |
| ss_0638w2kry | / (scrolled) | Pricing + footer |
| ss_9791rxh6q | / | Profile dropdown («Go to Platform» / «Log out») |
| ss_5322bqcrj | /teams/new | Authenticated catalog (Marketing, Sales, …) |
| ss_36854sq4t | /office | 404 (без team) |
| ss_08776a6dz | /dashboard → /teams/new | Same as 5322 |
| ss_3881hnakh | /teams/new (expanded Marketing card) | Workflow + Output details |
| ss_1419a4vuy | /teams/new?view=billing | Paywall: 4 tariffs + stats + Polar callout |
| ss_2765jihir | /teams/new?view=billing (scroll) | BYOK section visible |
| ss_18243zxyl | /teams/new?view=billing (bottom) | Same view, payment method |
| ss_8479nge2l | /tasks | 404 |
| ss_56765enw2 | /settings | Identity (production-agent-01) + Region IAD |
| ss_1043h3g1h | /settings/api-keys | 5 BYOK provider cards |
| ss_7984mr4iw | /settings/integrations | 11 Composio toolkits |
| ss_1456yf318 | /settings/channels | No cell found |
| ss_76534m0mj | /settings/advanced | 6 accordion sections |
| ss_1195e5f0v | /settings/preferences | Default preset + Autonomous + Rituals |
| ss_9954vnjeb | / (post-settings) | Coordinator input UI |
| ss_8850yhqgq | / (wizard step 1) | Team size selection |
| ss_084077v5w | / (wizard step 2 RU) | Use as-is / Adjust plan / etc. (Russian via auto-translate) |

Total: 22 screenshots saved (via MCP Chrome screenshot tool).

## API endpoints discovered

### Working (200)

- `GET /api/cell/sessions` → `{sessions: []}`
- `GET /api/cell/keys` → `{providers: [9 items]}`
- `GET /api/cell/skills` → `{skills: []}`
- `GET /api/cell/services` → `{services: []}`
- `GET /api/catalog/teams` → 13 team presets (18327 chars JSON)
- `GET /api/integrations` → 11 Composio toolkits
- `GET /api/support/unread-count` → `{count: 0}`
- `GET /api/assets/agents/{id}/{state}.png?v={ver}` → PNG sprites

### Returns 404 (require active cell, likely)

`/api/me`, `/api/user`, `/api/account`, `/api/billing/*`, `/api/cell`, `/api/cell/agents`, `/api/cell/teams`, `/api/cell/billing`, `/api/cell/status`, `/api/cell/region`, `/api/cell/channels`, `/api/cell/secrets`, `/api/cell/preferences`, `/api/cell/agent-config`, `/api/cell/webhooks`, `/api/cell/integrations`

## Что НЕ исследовано (out of scope для бесплатного аккаунта)

- /office UI (требует активной cell)
- /tasks UI
- /activity feed
- Workflow execution / streaming
- WebSocket connections (нет активных без cell)
- Coordinator chat post-wizard (likely paid)
- Pixel-Department-в-Office canvas (live agent positioning)
- Channels-flow (Slack/Discord input → cell)
- Sandbox / code-execution
- Memory persistence в реальной задаче
- BYOK token-saving в реальной нагрузке
- Polar checkout flow
- Webhooks dispatch

## Что НЕ выполнили (low-priority)

- Не извлекли full JS bundle через source-map (deobfuscation potentially useful, но дорого)
- Не открыли Settings → Business Profile (низкий приоритет)
- Не покликали все вложенные Advanced accordion-секции (System Status / Agent Config / Webhooks / Tool Access / Skills / Services — но названия дают понимание)
- Не вошли в Composio backend для inspection их toolkits
- Не captured все incident-banner details (was on 2026-05-08)

## Источники данных в этом анализе

- Live MCP Chrome session, ~30 минут active time
- ~22 screenshots
- ~7 successful API JSON-responses
- get_page_text on ~10 pages
- read_page (a11y tree) on ~5 pages
- JavaScript-inspections (fonts, canvases, frameworks, cookies, localStorage)

## Reliability / confidence levels

| Finding | Confidence |
|---|---|
| Tech stack (Next.js 15 / Clerk / Sentry / GA4) | 100% |
| Pixel Department = canvas 2D + PNG sprites | 100% |
| 13 team presets с workflow definition | 100% (API json) |
| 11 Composio toolkits | 100% (API json) |
| 9 BYOK providers | 100% (API json) |
| 4 pricing tiers + 1 free | 100% (UI) |
| Cell-per-team architecture | 95% (явный UI-текст + регион assignment) |
| 1 T$ = $1 курс | 100% (UI «1 credit = $1.00») |
| BYOK -80% saving | 100% (UI claim) |
| Autonomous mode mechanics (heartbeat + cron + PARA) | 100% (UI labels + descriptions) |
| Sprite sheet size 13.5 MB | 100% (Content-Length header) |
| Coordinator wizard structured (not LLM) | 95% (no LLM call made when typing free text) |
| Polar.sh payment provider | 100% (UI text) |
| IAD region (us-east) | 100% (UI text) |

## Next steps (для команды)

1. **Передать `RECONSTRUCTION-NOTES.md` Tech Lead'у** для пересмотра ADR-004 (canvas vs PixiJS), ADR-009 (ускорение cell-per-team), ADR-013 (Composio vs MCP).
2. **Передать Founder'у** для GTM-стратегии: позиционирование (3 wedges), BYOK на Wave 3, vertical templates для РФ.
3. **Бюджет на pixel-art ассеты** — Founder + Designer договорить подрядчик.
4. **Risks update** — добавить R-13/R-14/R-15 в `risks/REGISTER.md`.
5. **Дополнительный анализ при payment-trigger** — если в будущем оплатим Teamly 5 ($29) на 1 месяц, можно дообразовать `04-pixel-department.md` с живым Office view + захват WebSocket-сообщений Agent runtime. Это даст +50% information density. ROI на $29 — приличный.

## Сроки

- Session старт: ~ 13:50 (Москва)
- Session завершён: ~ 14:30 (Москва), ~40 минут active engagement
- Compilation: ~ 15 минут
- **Total: ~55 минут**

Это в 2× быстрее изначальной оценки (~2 часа в `PLAN.md`). Authenticated session с активным аккаунтом сильно ускорил.
