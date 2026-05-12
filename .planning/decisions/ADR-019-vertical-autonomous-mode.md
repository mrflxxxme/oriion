# ADR-019: Vertical-specific Autonomous Mode + «Знания команды» (PARA)

- **Status:** Accepted

## Decision

### Wave 2 (core infrastructure)

**Persistent memory across sessions** (расширение ADR-011):
- Conversation history per agent (FIFO + summarization)
- Memory entries не TTL-привязаны к session

**Cron scheduler** (`backend/src/autonomy/`):
- Dramatiq + cron-syntax
- Per-cell cron-jobs с budget-limits (R-04)
- Deadman switch: 7+ дней нет owner activity → pause autonomy
- Heartbeat (Wave 3): per-agent check каждые 30 мин на «unfinished work»

**Webhooks (Wave 3+):**
- Trigger от external events (Telegram-message, email-arrival, integration-event)
- Routed через MCP-server в Cell event-bus

### Wave 3 (vertical rituals + «Знания команды»)

#### «Знания команды» (PARA Workspace, переименовано для RU-UX)

4 категории (русские названия):
- **Проекты** — активные с deadlines
- **Сферы** — long-term areas
- **Ресурсы** — материалы, шаблоны, brand book
- **Архив** — completed

UI panel в Cell-dashboard, 4 вкладки, drag-and-drop, auto-archive.

#### Vertical Rituals Catalog

**Per vertical-template — pre-baked рутины** (ритуалы) с правильным cron + prompts:

**WB-Селлер команда (10 ритуалов):**
- `06:00 daily`: проверка цен топ-5 конкурентов по артикулам клиента
- `09:00 mon-fri`: dashboard продаж за вчера
- `mon 10:00`: weekly sales report для owner
- `every 4 hours`: monitoring остатков FBO
- `last day of month`: monthly summary
- `alert if`: конверсия артикула падает >10%
- `alert if`: рейтинг товара падает <4.5
- `alert if`: остатки FBO <7 дней
- `wed 11:00`: анализ trending категорий
- `fri 16:00`: weekend-promo planning

**Маркетинг-агентство РФ (12 ритуалов):**
- `mon 09:00`: weekly content-plan для активных клиентов
- `daily 18:00`: trending topics in client niches
- `alert if`: trending тема в нише клиента → draft-пост
- `end-of-month 17:00`: client report draft
- `wed 10:00`: competitive audit для клиентов
- ... (детально в Phase 03.4)

**Telegram-крейтор (8 ритуалов):**
- `daily 10:00`: контент-идеи на сегодня
- `weekly mon`: analytics-отчёт
- `every Tue/Thu 19:00`: post-time-optimal суggest
- ...

**ИП-Бухгалтерия (6 ритуалов — все с approval-mode):**
- `daily 09:00`: проверка статусов платежей в Эльбе
- `5 days before deadline`: reminder + check готовности
- `at incoming ФНС-letter`: extraction + analysis + draft-ответ (approval required)
- `quarterly`: проверка налоговых режимов оптимальности
- ...

**СМБ-Sales (8 ритуалов):**
- `daily 10:00`: lead-scoring новых лидов
- `daily 17:00`: follow-up «забытых» >3 дня
- `weekly`: sales-pipeline report
- `alert if`: hot-lead появился (по custom score)
- ...

#### Outcome Profiles (3 пресета)

- **«Тихий помощник»** (= Hands-off): 1-2 рутины/день, daily-summary only
- **«Активная команда»** (= Stay Informed): 4-6 рутин/день, weekly-report
- **«Я делегирую всё»** (= Full Hustle): 10+ рутин/день, proactive actions
- **Custom:** granular per-ritual on/off

### Safety (R-04, R-19, R-20)

#### Budget hard-caps
- Per-cell daily budget (e.g. 1000 кредитов/день default)
- Per-ritual per-day max executions
- Kill-switch при spend-rate >threshold

#### Disclaimer & Consent (R-19 mitigation)
- При включении autonomy — explicit opt-in checkbox
- Clear list of actions, которые будут происходить
- Юр.copy: «Вы соглашаетесь, что AI-агенты будут выполнять следующие действия без вашего явного подтверждения каждый раз: [список]. Вы можете отменить или приостановить любое время.»

#### Approval-gates для high-stakes
- ИП-Бухгалтерия рутины: ВСЕ write-actions требуют human approval
- Юр-задачи: автономный анализ (read-only), действия — только approval

#### API stability monitoring (R-20)
- Health-check WB Партнёры / Ozon Seller / 1С REST / Эльба API каждые 5 минут
- При >5% error rate → auto-pause связанных rituals + alert owner
- Graceful degradation: уведомление пользователя, что rituals временно paused

### Audit

- Все autonomous-actions → `audit.audit_log` с тегом `autonomous_action`
- Daily digest для owner: «Что сделали автономные агенты сегодня»
- Weekly summary email при включённом autonomous-режиме

## Consequences

- Vertical-specific rituals = killer-функционал per template
- «Знания команды» (PARA) даёт long-term retention

## Links

- Risks: [R-04](../risks/REGISTER.md), [R-19](../risks/REGISTER.md), [R-20](../risks/REGISTER.md)
- Phase: 02.9 (core autonomy infra), 03.4 (rituals + PARA)
- Related ADRs: ADR-011 (memory), ADR-017 (vertical-templates), ADR-014 (security)
