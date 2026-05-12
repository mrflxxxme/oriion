# 01 — User Journeys

> Captured flows. UX-метки и URL-пути зафиксированы из live session.

## 1. Unauthenticated landing (Discovery)

Path: `https://teamly.to/`

- **Hero:** пиксельный «Координатор» (sprite formal01 в костюме с портфелем), speech bubble «What task do you want to solve?»
- **Form:** text input «e.g. A marketing team that creates content...» + send-button
- **Quick chips:** [Marketing team] [Dev team] [Sales team]
- Header nav: HOW IT WORKS / PRICING / (avatar если залогинен)
- Footer: Privacy / Terms / Cookies / Licenses

При вводе текста / выборе chips → запускается **Coordinator Wizard** (а не LLM!) — это структурированный визард, не chat.

## 2. Coordinator Wizard (4-шаговый, без LLM)

Step 1: «Team size»
- Just me / Small team (2-5) / Growing team (6-15) / Large team (15+)

Step 2: «How should I use the task you described above?»
- Use as-is / Adjust plan / Show wide demographic group / Continue research / Back

(Дальнейшие шаги не пройдены, но pagination shows ~4 шагов.)

**Implementation note:** wizard рендерится прямо на landing/homepage. После завершения wizard перекидывает на `/teams/new?...` с pre-selected preset.

## 3. Sign-in / Sign-up

- Provider: **Clerk** (clerk.teamly.to)
- Method: email/password + социальные провайдеры (Google и др., точно не зафиксированы)
- Avatar/initials: ID `img.clerk.com/...` с зашитыми initials base64.
- Profile dropdown (top-right):
  - User name (e.g. "КИРИЛЛ")
  - Email
  - "GO TO PLATFORM" button
  - "LOG OUT" button

## 4. Onboarding (для нового пользователя)

URL: `https://teamly.to/dashboard` → автоматический redirect → `https://teamly.to/teams/new`

Headline: **"Hire Your First AI Team"**
- Sub: «Teamly is not another chatbot. Pick a workflow team with specialist agents, shared context, tool access, and a concrete output.»
- 3 value checkmarks: «Assign goals» / «Agents coordinate» / «Get deliverables»
- Tab: **«Ready Teams»**
- Filters: Search bar + Category dropdown (Category / Name)
- **Sections:**
  - WORKFLOW TEAMS (более «структурированные», ordered pipelines)
  - TEAMS (классические teams)
- Каждый team-card:
  - Icon-emoji + Name
  - Agent count
  - Short description
  - Pixel-art sprites (canvas) of agent characters with names below
  - Click «Hire» — expands card → shows WORKFLOW steps + OUTPUT description
  - Second click «Hire» (после раскрытия) → **paywall**

## 5. Paywall (Free plan → upgrade)

При попытке «Hire» с free plan:
- Toast: «Team limit reached (0/0). Upgrade your plan.»
- Redirect: `/teams/new?view=billing`
- View: BILLING

URL: `https://teamly.to/teams/new?view=billing`
- 4 plan cards (Teamly 5/15/30/Enterprise)
- Stats sub-section:
  - CREDITS USED: 0.00 (0 agents)
  - BUDGET SPENT: $0.00 (1 credit = $1.00)
  - CREDITS REMAINING: 0.00 ($0.00 remaining)
- PAYMENT METHOD section: "NO BILLING ACCOUNT YET. Choose a plan above to create a billing account and manage payment details securely in **Polar**."
- **BYOK promo:** "SAVE 80% ON CREDITS — Connect your own Anthropic or OpenAI key. Use your tokens directly — pay only a small platform fee instead of full credit price."

## 6. Sidebar navigation (когда есть team)

Left sidebar (постоянная):
- **+ NEW TEAM** dropdown
- **OFFICE** (current view)
- **TASKS** (404 без team)
- **ACTIVITY** (404 без team)
- **COORDINATOR** section header
  - Coordinator avatar card (status: ONLINE 🟢 / ACTIVE)
- **TEAM MEMBERS (0)** section with + button
- Bottom: **SETTINGS** / **SUPPORT** / user-card («Owner • No Plan»)

## 7. Settings (доступно даже на Free plan)

URL: `https://teamly.to/settings/*`

Sidebar:
- **ACCOUNT**
  - Preferences (`/settings/preferences`)
  - Business Profile (`/settings/business-profile`)
- **TEAM**
  - General (`/settings` — Identity + Region)
  - API Keys (`/settings/api-keys`)
  - Team Secrets (`/settings/secrets`)
  - Integrations (`/settings/integrations`)
  - Channels (`/settings/channels`)
  - Advanced (`/settings/advanced`)

Поведение без активного cell: некоторые табы (Channels) показывают «No cell found for this user — Retry».

## 8. Preferences UX (главная конфигурация)

`/settings/preferences`:
- **DEFAULT TEAM PRESET** — 13 пресет-карточек на выбор (icon, name, description, agents count, plugins count).
- **PLUGIN OVERRIDES** — toggle:
  - Exa Search ("Web search and page crawling")
  - Composio ("1000+ app integrations")
  - Team Management ("Hire/fire agents, request secrets")
- **AUTONOMOUS MODE** — главная опция: "Enable persistent memory, proactive heartbeat, and scheduled tasks."
  - Включает: Memory + Heartbeat (30 min interval) + Cron + **PARA Workspace** (Projects/Areas/Resources/Archive)
- **RITUALS** — recurring scheduled tasks для autonomous-режима. По умолчанию:
  - `nightly-consolidation`: cron "Daily at 2:00 AM"
  - `morning-briefing`: cron "Daily at 8:00 AM"
- **OUTCOME PROFILE** — preset плотности автономии:
  - Hands-off (2 daily jobs)
  - Stay Informed (4 daily check-ins + weekly summary)
  - Full Hustle (4 daily rituals + max automation)
  - Custom (granular control)
- **PROFILE** sub-options: Default / Startup Hustle / Enterprise Cadence

## 9. Advanced settings

`/settings/advanced`:
- SYSTEM STATUS
- AGENT CONFIG
- WEBHOOKS
- TOOL ACCESS
- SKILLS
- SERVICES

Каждый — accordion (collapsed by default). «Power-user settings for your cell.»

## 10. Coordinator chat (post-onboarding, paid)

Free-tier user проходит wizard, не получает чат. Paid-tier presumably имеет «Talk to Coordinator» с реальным LLM-chat (не подтверждено — не оплачивали).

## 11. Support

Доступен через нижнюю кнопку «SUPPORT» в sidebar. Возможно ticketing-чат (использует endpoint `/api/support/unread-count`).

## Navigation map (для AI-агентов)

```
/                         Landing + Coordinator Wizard
/teams/new                "Hire Your First Team" + catalog
/teams/new?view=billing   Billing / Paywall
/teams/new?view=team      ? (предполагается)
/dashboard                Redirect → /teams/new (если нет team)
/office                   404 (без активной team)
/tasks                    404 (без активной team)
/settings                 General settings (identity + region)
/settings/preferences     Preset + Autonomous + Rituals
/settings/business-profile (не открывали)
/settings/api-keys        BYOK (9 providers)
/settings/secrets         Team Secrets
/settings/integrations    Composio toolkits (11)
/settings/channels        Messaging platforms
/settings/advanced        System/Agent/Webhooks/Tools/Skills/Services
```

## Скриншоты захвачены

Все скриншоты сохранены через MCP с уникальными ID (ss_*). Ключевые:
- Landing (Coordinator with task input)
- How it works section
- Pricing 3-tariff card
- Profile dropdown
- /teams/new catalog
- /teams/new expanded Marketing Team card
- /teams/new?view=billing (4 tariffs + stats + BYOK)
- /settings (Identity + Region IAD)
- /settings/api-keys (5 BYOK providers visible)
- /settings/integrations (11 Composio toolkits)
- /settings/channels (no cell found state)
- /settings/advanced (6 accordion sections)
- /settings/preferences (full config)
- Coordinator wizard step 1 (team size)
- Coordinator wizard step 2 (use as-is / adjust plan / etc.)
