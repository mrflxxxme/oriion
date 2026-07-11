# Open Questions — активные founder-decisions

> Только открытые вопросы, требующие решения founder'а. Каждый вопрос — с конкретным дедлайном и owner'ом.

## Юр.инфраструктура

| # | Вопрос | Варианты | Дедлайн | Owner |
|---|---|---|---|---|
| OQ-02 | ООО vs ИП на УСН | ООО (для ЮKassa B2B, реестра ПО) / ИП на УСН (дешевле, проще) | До открытия ЮKassa | Founder |
| OQ-03 | Юрист на retainer'е | Зарцын / ЕПАМ / Бранан Legal / разовые консультации | ~~До Wave 1 (запуск trial)~~ **просрочен** (Wave 1 закрыта 2026-07-10 без юриста) → до W2 02.0 friend-validation / public beta; гейтит OQ-32/33 (01.11) | Founder |
| OQ-04 | Уведомление РКН об операторе ПДн | Обязательно по закону | До prod-launch (submitted, dev unblocked) | Founder + юрист |
| OQ-05 | Регистрация товарного знака | Роспатент, 6 мес процедура | До публичной беты (Wave 2) | Founder + патентный поверенный |

## Команда

> **Status: all 4 closed `N/A` per [P-INIT-5](./decisions/ADR-028-policies-registry.md#policies-canonical-home)** — team model = solo founder + 11 persistent Opus AI-agents (see [ADR-023](./decisions/ADR-023-ai-team-runtime.md), [DECISION-3](./decisions/ADR-028-policies-registry.md#decision-3)). R-29 closed via founder vertical expertise.

| # | Вопрос | Resolution | Closed-by | Owner |
|---|---|---|---|---|
| OQ-13 | Co-founder / CTO | **соло** (founder = solo) | P-INIT-5 / Session 1 GRILL | Founder |
| OQ-14 | Senior Backend Python | **N/A** (backend-implementer AI role) | P-INIT-5 / Session 1 GRILL | Founder |
| OQ-15 | Senior Frontend (Vite+React+TanStack+Canvas) | **N/A** (frontend-implementer AI role) | P-INIT-5 / Session 1 GRILL | Founder |
| OQ-16 | Бумажные правила (40ч неделя, отпуска) | **N/A** (no human hires Wave 0-3) | P-INIT-5 / Session 1 GRILL | Founder |

## Финансы (project-scope only)

> **Founder-personal финансовые решения** (funding strategy, burn-budget, runway, personal capital allocation, pre-seed timing) — **out-of-scope project documentation** per Session-2026-05-15 decision. Founder самостоятельно управляет этими решениями вне репозитория. Project tracks ONLY: AI dev cost caps (см. `.claude/agents/_shared/cost-budget.yaml`) + billing infrastructure (ЮKassa).

| # | Вопрос | Варианты | Дедлайн | Owner |
|---|---|---|---|---|
| OQ-17 | ~~Funding-стратегия~~ | **Closed `out-of-scope` per Session-2026-05-15** — founder-personal decision, не project concern | N/A | Founder |
| OQ-18 | ~~Стартовый burn-бюджет~~ | **Closed `out-of-scope` per Session-2026-05-15** — founder-personal decision; project tracks AI dev caps only в cost-budget.yaml | N/A | Founder |
| OQ-19 | ЮKassa открытие | Старт процедуры (5–10 дней) | До Wave 1 (billing) | Founder + бухгалтер |

## Брендинг

| # | Вопрос | Варианты | Дедлайн | Owner |
|---|---|---|---|---|
| OQ-09 | Доменное имя и бренд | ✅ **Resolved 2026-07-10:** бренд = **«Профики»** (slug `profiki`), домен `профики.online` (staging: `staging.профики.online`); «oriion» остаётся внутренним codename (репо `mrflxxxme/oriion`). Ренейм в коде выполнен (01.8c PR-2, #111). Дизайн-направление — [ADR-031](./decisions/ADR-031-design-direction-restyling.md) (nordic base, pixel-герои — опциональный скин) | — (закрыт) | Founder + Marketing |

## Маркетинг (не блокирует MVP)

| # | Вопрос | Варианты | Дедлайн | Owner |
|---|---|---|---|---|
| OQ-21 | Каналы лидогенерации | Telegram-канал founder / Хабр / vc.ru / paid ads | До Wave 2 | Founder + Marketing |
| OQ-22 | Первые friends-клиенты per template | Список 30+ потенциальных (mix: generic SMB для horizontal + 5–8 agencies + 5–8 TG-creators) | До Wave 1 launch | Founder |
| OQ-31 | **Позиционирование personal-vs-SMB** | «Твои личные ассистенты» расширяет ТЗ — теперь preset позиционируется и для personal-users. Уточнить landing-copy + ICP-сегментацию для horizontal vs B2B vertical (Solo-тариф уже поддерживает personal-mode per ADR-008). | До Wave 1 launch (landing copy) | Founder + Marketing |

## Telegram Business API (01.11 — перенесена в W2+, RW-05)

| # | Вопрос | Варианты | Дедлайн | Owner |
|---|---|---|---|---|
| OQ-32 | **Business API privacy & consent UX detail** | Точные wording-и consent-screen-а + 152-ФЗ disclosure + Privacy Policy updates для Telegram Business integration per [ADR-030](./decisions/ADR-030-telegram-business-api.md) | Гейтит 01.11 (перенесена в W2+, RW-05) | Founder + юрист |
| OQ-33 | **РКН-уведомление update — Business API as additional ПДн processing** | Подача обновления через ГосУслуги — Bot читает private DM-content → новые категории ПДн | Гейтит 01.11 (перенесена в W2+, RW-05) | Founder + юрист |

## Wave 2+ assets

| # | Вопрос | Варианты | Дедлайн | Owner |
|---|---|---|---|---|
| OQ-25 | Pixel-artist для 5 vertical-героев | Freelance через FL.ru / Хабр / Кворк | До Wave 2 Phase 02.1 | Founder + Designer |
| OQ-26 | PoC MCP-серверов для РФ-API | Spike-проекты для Bitrix24 / amoCRM / 1С / Эльба | До Wave 2 Phase 02.4 | Senior Backend |

## Сводка (sync 2026-07-11: Wave 1 закрыта — gate wave-1-to-2 PASS 2026-07-10; Wave-1-дедлайны переезжают на W2)

**Required до prod-launch:** OQ-04 (final РКН confirmation; dev unblocked — РКН-уведомление submitted)
**Гейтят 01.11 (Telegram Business API, W2+, RW-05):** OQ-32, OQ-33 (Business API privacy + РКН-уведомление update)
**Required до W2 02.0 (friend-validation) / public beta:** OQ-22, OQ-31 (friends-list + positioning), OQ-03 (юрист), OQ-02 + OQ-19 (юр.лицо + ЮKassa — гейтят 01.3b, RW-04)
**Не гейтят текущую работу (параллельно, W2+):** OQ-05, OQ-21, OQ-25, OQ-26
**Resolved:** OQ-09 (бренд «Профики» / профики.online, 2026-07-10)
**Closed `N/A` per P-INIT-5 (solo + 11 AI model):** OQ-13, OQ-14, OQ-15, OQ-16
**Closed `out-of-scope` per Session-2026-05-15 (founder-personal finance):** OQ-17, OQ-18
