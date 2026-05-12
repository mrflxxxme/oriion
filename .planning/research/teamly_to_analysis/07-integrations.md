# 07 — Integrations & External Connectors

## Главная находка: Composio как Integration Hub

Teamly **не строит свой connector framework** — они полагаются на **Composio.dev** как managed-сервис для всех 3rd-party tool-integrations. Это снижает сложность разработки в 10×.

## Composio toolkits (видимые в catalog)

Из `/api/integrations` — 11 curated toolkits:

| `composioSlug` | DisplayName | Category | Description |
|---|---|---|---|
| airtable | Airtable | productivity | Create, list, update, and delete Airtable records |
| github | GitHub | developer | Create and manage GitHub issues, PRs, comments |
| gmail | Gmail | communication | Read, search, send, and draft Gmail messages |
| googlecalendar | Google Calendar | calendar | Create, list, update, delete events; find free time |
| googledrive | Google Drive | storage | List, get, upload, search files |
| googlesheets | Google Sheets | productivity | Lookup, read, batch-update, append rows/columns |
| hubspot | HubSpot | crm | (CRM operations) |
| linear | Linear | productivity | Create, list, update issues + comments |
| notion | Notion | productivity | Query DBs, create/update pages, append blocks |
| slack | Slack | communication | User-level integration |
| slackbot | Slack (Bot) | communication | Bot-level integration |

Все toolkits с `managedAuth: true` — OAuth handled Composio side. UI клиента — просто кнопка «Connect».

## Composio plugin (override)

В Preferences есть toggle для **Composio plugin**, заявляющий «1000+ app integrations». Это указывает, что:
- Кураторские 11 видны для casual users
- При включении Composio plugin полностью — доступны все 1000+ apps Composio's library через advanced UI

Это **smart curation strategy**: показывают 11 — топовых для SMB, но не закрывают power-users от full library.

## BYOK для Composio

В `/settings/api-keys` есть слот для `composio` BYOK. Это означает, что:
- По умолчанию Teamly использует **свой Composio API key** для всех клиентов (managed offering)
- Power-user может connect свой Composio account → получает свои rate-limits, свой billing, свой compliance

## Channels (input integrations)

`/settings/channels` — для messaging platforms (Slack/Discord/Telegram/etc.) которые могут «писать в cell». В отличие от Composio toolkits, channels — это **input для агентов**, не tools.

Без активной cell этот tab показывает «No cell found for this user — Retry».

Channels механика:
- User connects Slack/Discord channel
- Сообщения в channel приходят к Coordinator (или routed агентам по правилам)
- Agents отвечают back в channel
- Это превращает teamly cell в **multi-channel AI worker**

## Webhooks (output integrations)

В Settings → Advanced есть `WEBHOOKS` accordion. Не открывали (требует активной cell), но предполагается:
- Outbound: события cell → user's webhook endpoint
- Useful для интеграции с custom systems

## Skills и Services (advanced abstractions)

Из Settings → Advanced:
- **SKILLS** — extensible capability per agent
- **SERVICES** — long-running background services per cell

Empty for free-tier. На Pro / Enterprise предполагается:
- Skills marketplace или custom skills via API
- Services: RAG indexer, custom cron, etc.

## API Keys (BYOK extensions)

Beyond LLM providers, BYOK also covers **search APIs**:

| Provider | Cost benefit | Use case |
|---|---|---|
| anthropic | -80% on inference | Sonnet/Opus tasks |
| openai | -80% on inference | GPT-4o tasks |
| google | -80% on inference | Gemini |
| openrouter | -80% on inference | Multi-model routing |
| minimax | -80% on inference | Chinese LLM (M1, MiniMax) |
| zai | -80% on inference | Z.AI / GLM (Chinese) |
| brave | Direct billing | Search API |
| exa | Direct billing | Neural search API |
| composio | Direct billing | Integration hub |

## Что НЕТ среди интеграций (notable для нашего рынка)

Teamly **не имеет** интеграций с РФ-сервисами:
- ❌ Bitrix24, amoCRM (не в Composio's standard catalog)
- ❌ 1С, Контур, Эльба
- ❌ Telegram (есть в Composio, но Teamly не curated)
- ❌ Яндекс.Диск, Яндекс.Почта
- ❌ VK, ВКонтакте Workspace
- ❌ MyWarehouse / МойСклад
- ❌ Российские банки / финтех

Это **наш wedge**: вертикальная локализация интеграций для РФ-рынка через нашу собственную connector framework или custom Composio toolkits.

## Composio limits & dependencies

Зависимость от Composio привносит risks:
- Vendor lock-in (если Composio закроется или меняет pricing)
- Rate-limits Composio (shared между всеми Teamly tenants)
- Composio outage = teamly outage для tool-use
- TOS Composio (Teamly должен соблюдать; если Composio лимитирует определённые use-cases — Teamly теряет fcionality)

С другой стороны:
- Скорость build: 11 toolkits в production day-1 — было бы 11 недель custom dev work
- Operational overhead: 0 для OAuth/auth/refresh
- Quality: Composio решает known issues (token refresh, retries, error handling)

## Реконструкция для нашего roadmap

См. `RECONSTRUCTION-NOTES.md`. Кратко:

1. **Composio vs custom MCP — стратегический выбор.** Composio даёт скорость, но не покрывает РФ-toolkits. Гибрид: используем Composio для глобальных (Gmail, GitHub, Notion), MCP для РФ-специфичных (Bitrix, amoCRM, 1С).
2. **Channels** — у нас этого пока нет в roadmap. Стоит добавить в Wave 3 (Telegram/Discord/Slack input для агентов). Это closes UX-loop с проактивными агентами.
3. **BYOK для всех LLM-провайдеров с дня 1** — у teamly это так. Наш ADR-002 уже multi-provider, но BYOK явно не выделен. Стоит добавить как Wave 3 фичу (вместо Wave 4) для enterprise-сегмента.
4. **Composio vs наш ADR-013 (MCP-протокол).** MCP сейчас более developer-friendly стандарт, Composio — более product-friendly. Мы можем поддерживать оба: MCP для tech-savvy custom, Composio (или его аналог) для GUI-юзеров.
