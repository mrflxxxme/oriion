# 03 — Architecture: Backend

## Ключевая концепция: «Cell»

В teamly.to **Cell = единица deployment per team**. Каждая «AI Team», которую нанимает пользователь, провизионится как отдельная **cell**, привязанная к региону (e.g. `iad — Ashburn, Virginia`).

> «The region is set during cell provisioning and cannot be changed after deployment. Contact support if you need to migrate to a different region.»

Это объясняет маркетинг **"Every plan includes dedicated infrastructure"** — это не миф, это реальная архитектурная модель.

Cell содержит:
- Agents (агенты команды)
- Memory (для autonomous-mode)
- Tool credentials / API keys
- Workflow state / sessions
- Cron jobs (rituals)
- Webhooks
- Channels (Slack/Discord/etc. inputs)

Tariff limits per «workspaces / AI teams»:
- Teamly 5: 3 workspaces / 3 AI teams
- Teamly 15: 5 / 5
- Teamly 30: 10 / 10

**Гипотеза:** «Workspace» = логическая группировка нескольких cells одного пользователя. Каждая cell = отдельный «AI team» (deployment unit).

## Auth / IAM

- **Clerk** (clerk.teamly.to subdomain) — managed identity provider
- JWT-based session через `__session` cookie + `__client_uat` для UAT timestamp
- Multi-app instance ID (`ins_39s293eemhnbQabIaHXxaOUTFqg`) — Clerk Production environment

## API surface (наблюдаемый)

Базовый URL: `https://teamly.to/api/`

### Подтверждённые endpoints

| Endpoint | Method | Использование |
|---|---|---|
| `/api/cell/sessions` | GET | Возвращает `{sessions: []}` — список сессий cell (вероятно chat-sessions с Coordinator-/agent-задачами) |
| `/api/cell/keys` | GET | Возвращает `{providers: [...]}` — BYOK-keys per cell. См. полный список ниже. |
| `/api/cell/skills` | GET | `{skills: []}` — установленные skills cell (пусто на Free / нет cell) |
| `/api/cell/services` | GET | `{services: []}` — running services cell |
| `/api/catalog/teams` | GET | Каталог team-presets (13 teams с полным workflow definition) |
| `/api/integrations` | GET | Список доступных Composio toolkits (11 шт.) |
| `/api/support/unread-count` | GET | `{count: N}` — для бейджа Support |
| `/api/assets/agents/<id>/<state>.png` | GET | PNG-sprite-sheet per agent + state. Immutable, `max-age=31536000`. |

### Endpoints, возвращающие 404 (не существуют в моём scope)

`/api/me`, `/api/user`, `/api/account`, `/api/billing/me`, `/api/billing/account`, `/api/billing/balance`, `/api/cell` (root), `/api/cell/agents`, `/api/cell/teams`, `/api/cell/billing`, `/api/cell/status`, `/api/cell/region`, `/api/cell/channels`, `/api/cell/secrets`, `/api/cell/preferences`, `/api/cell/agent-config`, `/api/cell/webhooks`, `/api/cell/integrations`

→ **Гипотеза:** многие из этих маршрутов существуют, но требуют активной cell (paid plan) — возвращают 404 при `cell_id = null`.

## BYOK providers (из `/api/cell/keys`)

9 поддерживаемых:

| Provider | Категория | Назначение |
|---|---|---|
| `anthropic` | LLM | Claude Sonnet, Opus |
| `openai` | LLM | GPT-4o, o1, etc. |
| `google` | LLM | Gemini |
| `openrouter` | LLM gateway | Multi-model proxy |
| `minimax` | LLM | MiniMax (Chinese, M1) |
| `zai` | LLM | Z.AI / GLM models |
| `brave` | Search | Brave Search API |
| `exa` | Search | Exa neural search |
| `composio` | Integrations | Composio API key (для всех toolkits) |

UI показывает только 5 (Anthropic / OpenAI / Brave / Exa / Composio), но backend поддерживает все 9.

## Default LLM stack (без BYOK)

Из маркетинга: "Teamly Dollars are used by your agents as they work across **Sonnet and Opus**" — стандарт = Anthropic Claude.

Pricing equivalent: $1 = 1 Teamly Dollar = некий объём Sonnet/Opus inference. Сколько именно — не раскрыто.

С BYOK: «pay only a small platform fee instead of full credit price» → -80%. То есть платформа берёт ~20% над raw compute cost (markup), без BYOK эффективно ~5×.

## Composio integration

Composio = MCP-style platform для подключения 3rd-party SaaS (Gmail, Slack, GitHub, etc.) — Teamly использует Composio как orchestration layer для всех «tools» агентов.

Каждый toolkit в `/api/integrations` имеет:
- `composioSlug` — ключ в Composio API
- `displayName`
- `description`
- `category` (productivity / developer / communication / calendar / storage / crm)
- `managedAuth: true` — OAuth-flow handled by Composio managed (нет setup'а для клиента, только нажать "Connect")

11 toolkits:
| Slug | Category |
|---|---|
| airtable | productivity |
| github | developer |
| gmail | communication |
| googlecalendar | calendar |
| googledrive | storage |
| googlesheets | productivity |
| hubspot | crm |
| linear | productivity |
| notion | productivity |
| slack | communication |
| slackbot | communication |

В Preferences page заявлено "1000+ app integrations" через Composio plugin override — это раскрывает Composio's full library, но Teamly выборочно показывает 11 curated. Остальные доступны через Advanced.

## Payments

- Processor: **Polar.sh** — modern, dev-focused payment platform (used by open-source projects). EU-based, subscription support, webhooks.
- Currency: USD only.
- "1 credit = $1.00" — explicit equivalence. Teamly Dollars NOT a separate currency, but a usage tracking unit.

## Storage / persistence

Не идентифицировано напрямую (нет visible DB-endpoint). Гипотезы:
- Cell state — likely Postgres per cell или per-region (shared с tenant_id)
- Sessions — Redis или PostgreSQL JSONB
- Audit — отдельная append-only стрим (вероятно)
- Vector store для memory — возможно pgvector или Pinecone

## Deployment regions

Только наблюдали `iad — Ashburn, Virginia` (AWS US-East-1 area). Маркетинг намекает на multi-region («Region is set during cell provisioning»), но other regions не зафиксированы.

## Webhooks (Advanced setting)

`WEBHOOKS` секция в Settings → Advanced. Не открывалась, но название говорит само за себя — outbound webhooks для events внутри cell.

## Skills & Services (Advanced)

`SKILLS` и `SERVICES` секции — likely plugin-like extensions для cell. Endpoint `/api/cell/skills` и `/api/cell/services` возвращают пустые массивы — без активной cell.

Гипотеза:
- **Skill** — capability агента (мелкий tool / chain).
- **Service** — long-running process в cell (e.g. RAG indexer, webhook dispatcher).

## Architecture diagram (reconstructed hypothesis)

```
[Browser] → [Next.js 15 (Vercel/Cloud)] → [API Layer]
                                            ↓
                                   [Clerk (auth)]
                                            ↓
                       [Cell Orchestrator (assigns/provisions cells)]
                                            ↓
                              [Per-tenant Cell (region-pinned)]
                              ├─ Agent runtime (Claude/OpenAI/etc.)
                              ├─ Sessions storage
                              ├─ Memory (autonomous-mode)
                              ├─ Tool secrets
                              ├─ Cron / Heartbeat scheduler
                              ├─ Webhook dispatcher
                              └─ Composio client (for integrations)
                                            ↓
                                   [Polar.sh (billing)]
                                            ↓
                                   [Sentry (errors), GA4 (analytics)]
```

## Hypotheses for our roadmap

См. `RECONSTRUCTION-NOTES.md` для полного gap-анализа. Кратко:
- Их «Cell» концепция = наш Уровень C/D мультитенантности (ADR-009). Они start with dedicated namespace per cell с дня 1 — это маркетингово сильно, но дорого.
- BYOK у них уже работает — нам стоит подумать о BYOK на Wave 4/5+.
- Composio как proxy для integrations — стоит ли нам тоже использовать готовый managed-сервис вместо собственного MCP-каталога?
