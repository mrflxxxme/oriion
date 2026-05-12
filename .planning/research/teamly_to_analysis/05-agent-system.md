# 05 — Agent System

## Концептуальная модель

```
[Cell (= AI Team, dedicated infra)]
   └── Coordinator (системный, всегда есть)
   └── 1..N Agents (= AI employees, наняты по тарифу)
         ├── Sprite character (e.g. "Mika", "Marcus")
         ├── Role (Content Strategist, Copywriter, …)
         ├── default_tools (subset of Composio + Search)
         ├── Memory (если autonomous mode включён)
         └── Permissions / scopes
```

«Team» в product UI = preset, который spawn'ит cell + набор agents с определённой workflow-цепочкой.

## Team-каталог (13 presets, из `/api/catalog/teams`)

### Workflow Teams (chained pipelines)

| ID | Name | Agents | Workflow chain |
|---|---|---|---|
| `marketing` | Marketing Team | 4 (Mika, Marcus, Scout, Hayden) | Scout (analyze trends) → Mika (briefs/calendar) → Marcus (write content) |
| `wf-content-marketing` | Content Marketing Team | 4 (Scout, Mika, Marcus, Nora) | Scout analyzes → Mika plans → Marcus writes → Nora produces video |
| `wf-sales` | Sales Team (Inbound) | 2 (Alex Sales, Rio) | Alex consults prospects → Rio qualifies, books calls, manages follow-ups |
| `lead-research` | Lead Research | 1 (Mark) | Calendly → lead research → scoring → Slack card |
| `writer` | Content Writer | 1 (Marcus) | Coordinator + copywriter for content tasks |
| `health-wellness` | Health & Wellness Team | 4 (Cadence, Pulse, Nutra, LabReader) | Wearables + meal logging + lab summaries + routines |
| `personal-effectiveness` | Personal Effectiveness | 4 (Oliver, Josh, Maksim, Zoya) | Goals + daily rhythm + focused calendar + voice journal |
| `hr` | HR Team | 4 (Hana, Kai, Emma, Finn) | Source → schedule/scorecard → onboarding → people ops |
| `book-oscar-case` | Book Writing — Oscar Case | 4 (Oskar, Marta, Eugene, Ivan) | ToC → draft → fact-check → style → PDF |

### Generic Teams (less structured)

| ID | Name | Agents |
|---|---|---|
| `dev` | Dev Team | 3 (Mika, Marcus, Vera) — architecture/frontend/backend/QA |
| `sales` | Sales Team | 3 (Scout, Marcus, Mika) — lead research/outreach |
| `research` | Research Team | 3 (Scout, Vera, Marcus) |
| `autonomous` | Autonomous Agent | 2 (Scout, Marcus) — persistent memory + heartbeat + cron |

## Workflow-step schema

Каждый team-preset содержит массив `workflowSteps`:

```json
{
  "agentName": "Scout",
  "action": "Analyze trends, competitors, and metrics",
  "output": "Weekly data report",
  "passesTo": "Mika"
}
```

Поля:
- `agentName` — кто выполняет
- `action` — описание задачи
- `output` — артефакт результата
- `passesTo` — следующий агент (или null если finalizing)

Это **жёстко зашитая state-machine** на уровне preset. Coordinator получает goal от user и распределяет шаги по этому DAG.

## Agent-archetype patterns

### Generic sprite pool (повторно используемые персонажи)

Sprites `creative01–creative11`, `formal01–formal05`, `hoodie07` etc. появляются в разных teams под разными именами. Например:
- Sprite `creative01` = Marcus (Copywriter в Marketing, Content Writer, Sales)
- Sprite `creative06` = Mika (Content Strategist, Dev architect — разные роли!)
- Sprite `hoodie07` = Scout (Content Analyst — multiple teams)

То есть **sprite ≠ identity**. Один sprite-character играет разные роли в разных teams. Это упрощает asset library (24 sprites покрывают все 13 teams + ~50 unique agent instances).

### Named/dedicated characters

Некоторые sprites уникальны и связаны с конкретной ролью:
- `oliver-goals`, `josh-morning`, `maksim-calendar`, `zoya-journal` — Personal Effectiveness specialists
- `hana-recruiter`, `kai-screener`, `emma-onboarding`, `finn-peopleops` — HR specialists
- `oscar-voice`, `marta-factcheck`, `eugene-stylist`, `ivan-designer` — Book Writing specialists
- `orchestra-health`, `pulse-health`, `nutra-health`, `labreader-health` — Health & Wellness

Эти роли — «vertical specialists», для них дизайнеры сделали уникальные ассеты.

## Agent runtime (гипотезы — backend не reverse-engineered)

Из observable: Sonnet и Opus mentioned как default models → **Anthropic Claude SDK**.

Возможные модули:
- LLM client (Anthropic + optional BYOK providers)
- Tool dispatcher (Composio API client + search APIs)
- Memory store (для autonomous mode) — vector DB?
- Heartbeat scheduler (cron-like для self-initiated work)
- Session log (для chat history)

## Plugin / Skill / Service abstraction

Из Preferences + Advanced UI:

| Понятие | Описание | Toggle |
|---|---|---|
| **Plugin** | Recommended high-level capability (e.g. Composio, Exa Search, Team Management) | Workspace-level toggle |
| **Skill** | Specific capability агента (мелкий tool / chain) | Per-cell Advanced |
| **Service** | Long-running process в cell (e.g. RAG indexer) | Per-cell Advanced |
| **Toolkit** | Composio app-integration (Gmail, Slack, etc.) | Connect/disconnect via OAuth |

Гипотеза:
- **Plugin** = bundle of skills + services, готовый к включению одним кликом.
- **Skill** = atomic capability, проявляется как tool в системе.
- **Service** = background-worker (cron, webhook, RAG).

## Coordinator mechanics

- На landing: «What task do you want to solve?» — **wizard, не LLM** (на free-tier).
- В sidebar: статус «ACTIVE» (с зелёной точкой) — implies real-time presence indication.
- Внутри cell: предполагается LLM-driven (Sonnet/Opus) для real chat и task decomposition.

Workflow gating: Coordinator wizard step 1 (team size) → step 2 (how-to-use) → step 3? → step 4? → spawn cell + redirect.

## Autonomous mode

Из Preferences:

> "Agents will remember conversations, check in proactively, and run scheduled tasks."

Components:
- **Memory** — conversations and knowledge persist across sessions
- **Heartbeat** — agents check in every 30 minutes for unfinished work
- **Cron** — agents can create scheduled jobs (consolidation, briefings)
- **PARA Workspace** — structured knowledge base (Projects/Areas/Resources/Archive, Tiago Forte methodology)

Default rituals:
- `nightly-consolidation` cron `Daily at 2:00 AM`
- `morning-briefing` cron `Daily at 8:00 AM`

Profiles:
- **Hands-off** — 2 daily jobs, minimal interruption
- **Stay Informed** — 4 daily check-ins + weekly summary
- **Full Hustle** — 4 daily rituals, max automation
- **Custom** — granular per-ritual control

Это **отдельная архитектурная ставка teamly.to**: они инвестировали в long-running, semi-autonomous mode (PARA + cron + heartbeat).

## Tool access

Из Settings → Advanced → Tool Access (accordion, не открывали глубже):
- Toggle per-tool per-agent (whitelist/blacklist)
- Permissions / scopes (read/write)

## Channels

`/settings/channels` — Connect messaging platforms (Slack/Discord/Telegram etc.) для **input** в cell. Agents могут реагировать на channel-messages в дополнение к UI-based задачам.

## Что МЫ нужно учесть в нашем дизайне

1. **Sprite-pool reuse** — наша 11-роль каталог может использовать ~7-10 sprite-archetypes повторно (например, generic Researcher, Writer, Coordinator). Это снижает требования к pixel-art бюджету.
2. **Vertical-specific named characters** для маркетинг-агентств / e-commerce-селлеров (наши Vertical-1/2) — Wave 2/3.
3. **Workflow templates** (наш ADR-003/Wave 3.2) совпадают с их `workflowSteps[]`-схемой. Уже близко к стандарту.
4. **Plugin/Skill/Service** разделение — у них умное; стоит обдумать для своей архитектуры (наш `tools` пока flat).
5. **PARA Workspace** (Tiago Forte) — интересная metaphor для memory; рассмотреть в Wave 5+ как часть episodic memory ADR-011.
6. **Heartbeat 30 min interval** — лимит автономного режима 48 ticks/day, manageable. Наша cost protection (ADR-014) должна выдерживать.
