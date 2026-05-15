# ADR-030: Telegram Business API integration для AI-команд

- **Status:** Proposed
- **Date:** 2026-05-15
- **Deciders:** Founder, Tech Lead (architect AI-role)
- **Supersedes:** N/A

## Context

Сессия 2026-05-15: при пересмотре Wave 1 scope-а founder указал: «учитывая последние обновления функционала TG-ботов, мы её ещё немного расширим после Wave 0».

За последние 12 месяцев Telegram Bot API получил серию обновлений, наиболее значимое для нашего use-case:

- **Telegram Business API (2024+):** bot действует от имени бизнес-аккаунта пользователя — читает входящие сообщения, отвечает, ставит реакции в личных чатах user-а. User активирует TG Business подписку + подключает bot в settings.
- **Mini Apps 2.0:** расширенный WebApp SDK (file inputs, biometric auth, settings storage, deep links с параметрами).
- **Telegram Stars + Payments 2.0:** нативная микро-валюта для in-app покупок.
- **Premium reactions + custom emoji**, multi-bot orchestration, topics в group chats.

Для нашей ниши (СМБ + personal productivity, RU) **Business API — primary use-case-усилитель**: солопренёры и микро-агентства могут переключить ответы на DM-запросы клиентов на AI-команду. Это killer feature для friends-pre-alpha и pre-Wave-2-public-beta.

Текущий план Wave 1 phase 01.10 содержит **telegram-mcp**, но описан тонко (read + post). Расширение требует архитектурного фиксирования: scope, security/privacy boundary, consent flow, retention model.

## Decision

В Wave 1 phase 01.10 telegram-mcp расширяется до scope **«Read + post + Business API»**. Mini App + Stars billing — **defer** в Wave 2 и Wave 3+ соответственно.

### Wave 1 scope (telegram-mcp v0.2)

| Capability | Wave 1 | Comment |
|---|---|---|
| Bot reads channel/group posts | ✅ | Existing Bot API |
| Bot posts to channel/group | ✅ | Existing Bot API |
| Bot reacts (emoji) | ✅ | Existing Bot API |
| Bot reads incoming DMs (via Business API) | ✅ NEW | User connects Business-bot в TG settings |
| Bot replies to DMs from user's account | ✅ NEW | Acts as user (consent required) |
| Bot manages reactions in user's private chats | ✅ NEW | Business API scope |
| Mini App контейнер | ❌ (W2) | Separate phase, Mini App SDK + bundler |
| Telegram Stars billing | ❌ (W3+) | Conflicts с ADR-008 unified ledger |
| Multi-bot orchestration | ❌ (W4+) | Power-user feature |

### Required user consent flow (privacy)

User действия в UI `/settings/integrations/telegram-business`:

1. **Read explanation:** «Bot будет читать твои входящие DM-ы и может отвечать от твоего имени. Это требует Telegram Business подписки.»
2. **Сheckbox-confirm** с явным wording: «Я понимаю, что AI-команда увидит содержимое моих private DM-ов»
3. **Optional scope-narrowing:**
   - [x] Read DMs (always required for any business-flow)
   - [ ] Auto-reply by AI without my approval (default OFF — manual approval mode)
   - [ ] Set reactions on my behalf (default OFF)
4. **Link to:** privacy-policy, 152-ФЗ disclosure
5. **Revoke flow:** one-click disconnect в UI → backend immediately revokes Business-token

### Compliance & 152-ФЗ

- **Storage of DM content:** ephemeral by default (≤7 дней for context window, then purged), opt-in для cell-memory-store при явном user-action «save это в Knowledge»
- **Encryption at rest:** все TG-DM-данные в DB шифруются `pgcrypto` per cell-key (ADR-014)
- **Audit log:** каждое чтение DM + каждый отправленный bot-message с consent_id reference
- **РКН-уведомление:** Phase 01.10 acceptance criteria включают «РКН-уведомление обновлено с описанием Business API as additional ПДн processing» (см. OQ-04)
- **152-ФЗ disclosure** в Privacy Policy: «при подключении Telegram Business AI-команда получает доступ к содержимому ваших private переписок до момента отключения интеграции»

### Architecture

```
backend/src/mcp/servers/telegram_mcp/
├── __init__.py
├── server.py                    # MCP server entry
├── tools/
│   ├── read_channel.py          # Bot API (existing scope)
│   ├── post_to_channel.py       # Bot API
│   ├── react_to_message.py      # Bot API
│   ├── business_read_dms.py     # NEW Wave 1: Business API
│   ├── business_send_dm.py      # NEW Wave 1: Business API + approval-gate
│   └── business_react_dm.py     # NEW Wave 1: Business API
├── auth.py                      # OAuth + Business connection token mgmt
├── consent.py                   # Consent enforcement + audit
└── retention.py                 # Ephemeral storage policy (≤7d default)
```

### Business-mode UX patterns

- **Manual approval mode (default):** bot drafts reply → user sees notification in TG (via secondary control-bot) → user approves/edits → send
- **Auto-reply mode (opt-in):** bot replies without approval; rate-limited (max 20 DMs/hour/contact, max 50/contact/day); soft-pause-on-keywords («жалоба», «возврат», «отказ»)
- **Read-only mode:** bot никогда не отвечает, только аналитика DM-flow (для Telegram-крейтор vertical Wave 1)

### Acceptance criteria для Wave 1 phase 01.10

- [ ] User может подключить Telegram Business bot через UI с явным consent flow
- [ ] Bot читает DMs по Business API в реальном времени (≤2 sec latency)
- [ ] Manual approval mode работает — bot drafts → user approves → send
- [ ] Auto-reply mode работает с rate-limits + soft-pause-keywords
- [ ] Revoke flow атомарен — disconnect → token revoke ≤30 sec, no orphan reads
- [ ] Ephemeral retention (≤7d) для DM-content активен; opt-in save в cell-memory работает
- [ ] Audit log записывает 100% DM-чтений и bot-sends с consent_id
- [ ] РКН-disclosure включает Business API
- [ ] Cost: Business API не добавляет fees от Telegram (Bot API free), только наш LLM-tokens

## Consequences

- ✅ **Killer feature для friends-pre-alpha:** «AI отвечает на DM-ы моих клиентов» = strong hook для солопренёров и микро-агентств
- ✅ **Telegram-крейтор vertical (Wave 1) усиливается** — Business API позволяет engagement-analytics + DM-funnel-management
- ✅ **Marketing-agency vertical (Wave 1) усиливается** — агентства управляют клиентскими DM-flows
- ⚠️ **Privacy risk высокий** — bot читает private переписку → consent UX обязан быть chrome-cleared + audit на 100%; единичная утечка = существенный репутационный hit (R-05 critical)
- ⚠️ **152-ФЗ compliance overhead** — РКН-уведомление обновляется + Privacy Policy expanded + retention policy enforced; +1 день к phase 01.10
- ⚠️ **+3–4 дня к Phase 01.10 scope** (Business API + consent flow + retention + audit + tests)
- 🔮 **Mini App (Wave 2)** надстраивается над Business API — даёт UX inside TG для approve/edit-flow
- 🔮 **Stars billing (Wave 3+)** интегрируется как parallel-channel к ЮKassa — отдельный ledger или unified TBD

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| Read + post only (current plan) | Минимальный scope | Не отражает killer-use-case для SMB | Слабый Wave 1 hook |
| + Business API + Mini App (W1) | Полный TG-experience в W1 | Mini App = +5–7 дней, ломает Wave 1 6-week timebox | Mini App в W2 |
| + Business API + Stars (W1) | TG-native billing | Конфликт с ADR-008 unified ledger, не решает приоритетную проблему W1 | Stars в W3+ |
| All-in W1 (Read + post + Business + Mini + Stars) | Full feature parity | +2 недели → Wave 1 8 weeks вместо 6 | Catastrophic timebox impact |
| Defer Business API to W2 | Wave 1 minimal | Теряется DM-killer-feature для friends-pre-alpha | Reduces W1 value-prop |

## Open Questions (создать в OPEN-QUESTIONS.md)

- **OQ-N (new): Business API privacy & consent UX detail.** Точные wording-и consent-screen-а + 152-ФЗ disclosure + Privacy Policy updates. Owner: Founder + юрист. Дедлайн: до старта Phase 01.10.
- **OQ-M (new): РКН-уведомление update — Business API as additional ПДн processing.** Подача обновления через ГосУслуги. Owner: Founder + юрист. Дедлайн: до старта Phase 01.10.

## Links

- Risks: [R-05](../risks/REGISTER.md) (data leak — critical), [R-08](../risks/REGISTER.md) (регуляторика), [R-33](../risks/REGISTER.md) (Business API privacy / 152-ФЗ exposure, opened с этим ADR)
- Phase: 01.10 (Wave 1 MCP servers — telegram-mcp v0.2), 02.X (Wave 2 Mini App), 03.X (Stars billing)
- Related ADRs:
  - [ADR-013](./ADR-013-mcp-protocol.md) — MCP catalog (telegram-mcp обновляется)
  - [ADR-014](./ADR-014-security.md) — DLP + capability sandboxing + encryption at rest
  - [ADR-008](./ADR-008-credits-billing.md) — Stars billing conflict / future integration
  - [ADR-017](./ADR-017-vertical-templates.md) — Telegram-крейтор + Marketing-agency verticals (consumers Business API)
  - [ADR-029](./ADR-029-master-agent-vertical-templates.md) — Master-Agent layer (Telegram-крейтор Master-Agent — primary consumer Business API workflows; Marketing-agency Master через client-DM-management ritual)
