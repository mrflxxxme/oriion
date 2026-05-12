# ADR-017: 5 vertical-templates как primary USP

- **Status:** Accepted

## Decision

### 5 стартовых vertical-templates (поэтапная выкатка)

| # | ID | Иконка | Name | Wave |
|---|---|---|---|---|
| 1 | `wb_seller_v1` | 🛒 | **WB-Селлер команда** | W0 (флагман) |
| 2 | `agency_marketing_ru` | 📈 | **Маркетинг-агентство РФ** | W1 |
| 3 | `telegram_creator` | ✍️ | **Telegram-крейтор / Курс-автор** | W1 |
| 4 | `accounting_ip` | 💼 | **ИП-Бухгалтерия (1С/Эльба)** | W2 |
| 5 | `smb_sales_ru` | 🎯 | **СМБ-Sales (Bitrix24/amoCRM)** | W2 |

### Composition per template

#### 1. WB-Селлер команда (W0)
- **Целевой клиент:** селлеры WildBerries (600K+ в РФ)
- **Agents (W0 — 3 + Analyst/SMM добавляются W1-2):**
  - Coordinator (deepseek-r1, sprite formal01, name «Алексей»)
  - Listing Writer (deepseek-v3, sprite creative01, name «Марк»)
  - Researcher (deepseek-v3, sprite hoodie01, name «Скаут»)
  - + W1: Analyst (deepseek-r1 + Pyodide, sprite formal03, name «Виктор»)
  - + W2: SMM (deepseek-v3, sprite creative04, name «Анастасия»)
- **Hand-drawn vertical-герой (W2):** «Селлер-Маркус»
- **Workflow steps:**
  1. Researcher: анализ топ-конкурентов по артикулу/нише
  2. Listing Writer: создаёт описание товара по результатам анализа
  3. Analyst (W1): анализ продаж + конверсии (через Pyodide CSV)
  4. SMM (W2): контент-план для Telegram-канала
- **MCP-tools (W2):** wb-partners-mcp, ozon-seller-mcp, telegram-mcp, yandex-disk-mcp
- **Vertical rituals (W3):**
  - 06:00 daily: проверка цен топ-5 конкурентов
  - 09:00 mon-fri: dashboard продаж за вчера
  - mon 10:00: weekly sales report для owner
  - alert при падении конверсии артикула >10%

#### 2. Маркетинг-агентство РФ (W1)
- **Целевой клиент:** маркетинг-агентства (30K+)
- **Agents:**
  - Coordinator (deepseek-r1, sprite formal02, name «Дмитрий»)
  - Researcher (deepseek-v3, sprite creative02, name «Скаут»)
  - Writer (deepseek-v3, sprite creative01, name «Марк»)
  - Designer (deepseek-v3, sprite creative05, name «Дизайнер»)
  - SMM (deepseek-v3, sprite creative04, name «Анастасия»)
  - + W2: Analyst (deepseek-r1 + Pyodide)
- **Hand-drawn vertical-герой (W2):** «SMM-Анастасия»
- **MCP-tools (W2):** bitrix24-mcp, amocrm-mcp, telegram-mcp, gmail-mcp, yandex-disk-mcp
- **Vertical rituals (W3):**
  - mon 09:00: weekly content-plan для клиентов
  - daily 18:00: monitoring trending тем в Telegram-каналах ниши клиентов
  - alert при появлении trending-темы → draft-пост
  - end-of-month: client report draft

#### 3. Telegram-крейтор / Курс-автор (W1)
- **Целевой клиент:** Telegram-каналы 50K+ авторов с monetization
- **Agents:**
  - Coordinator (deepseek-r1, sprite formal04, name «Координатор»)
  - Writer (deepseek-v3, sprite creative01, name «Марк»)
  - Researcher (deepseek-v3, sprite hoodie01, name «Скаут»)
  - Marketer (deepseek-v3, sprite creative03, name «Маркетолог»)
  - Community-manager (deepseek-v3, sprite creative06, name «Сообщество»)
- **Hand-drawn vertical-герой (W2):** «Крейтор-Денис»
- **MCP-tools (W2):** telegram-mcp, yandex-disk-mcp, gmail-mcp, getcourse-mcp (W3)
- **Vertical rituals (W3):**
  - daily 10:00: контент-идеи на сегодня (1 пост + 1 stories)
  - weekly mon: analytics-отчёт за неделю
  - email-серия sales-funnel (auto-trigger при покупке)

#### 4. ИП-Бухгалтерия (W2) — HIGH-STAKES vertical
- **Целевой клиент:** ИП в РФ (3M+, ОСН/УСН/НПД)
- **Agents (все с requires_human_approval=true для write-actions):**
  - Coordinator (deepseek-r1, sprite formal05, name «Координатор»)
  - Accountant (deepseek-r1 + yandex-pro, sprite formal02, name «Анна»)
  - Юрист (deepseek-r1, sprite formal03, name «Дмитрий»)
  - Reporter (deepseek-v3, sprite creative01, name «Репортёр»)
- **Hand-drawn vertical-герой (W2):** «Бухгалтер-Анна»
- **MCP-tools (W2-3):** 1c-rest-mcp, kontur-elba-mcp, kontur-extern-mcp, tinkoff-business-mcp, gmail-mcp
- **Vertical rituals (W3):**
  - daily 09:00: проверка статусов налоговых платежей в Эльбе
  - 5 дней до deadline отчётности: reminder + check готовности данных
  - при новом письме от ФНС: extraction + analysis + draft-ответ
- **Safety:** disclaimer mandatory на каждый ответ, никакой autonomy для финансовых проводок, approval mode by default

#### 5. СМБ-Sales (W2)
- **Целевой клиент:** СМБ-компании с CRM (100K+)
- **Agents:**
  - Coordinator (deepseek-r1, sprite formal01, name «Координатор»)
  - Sales-manager (deepseek-v3, sprite creative01, name «Sales»)
  - Researcher (deepseek-v3, sprite hoodie01, name «Скаут»)
  - Writer (deepseek-v3, sprite creative01, name «Писатель»)
  - SMM (deepseek-v3, sprite creative04, name «SMM»)
- **Hand-drawn vertical-герой (W2):** «Sales-Дмитрий»
- **MCP-tools (W2):** bitrix24-mcp, amocrm-mcp, telegram-mcp, gmail-mcp
- **Vertical rituals (W3):**
  - daily 10:00: lead-scoring новых лидов из CRM
  - daily 17:00: follow-up «забытых» лидов (>3 дней без contact)
  - weekly: sales-pipeline report
  - alert при появлении hot-lead (по custom score)

### Wave 3+ generic templates

После Wave 2 расширяем generic-presets (не vertical-specific):
- Content Marketing (universal)
- Sales Team (без CRM-вертикали)
- Dev Team (Wave 4 с sandbox)
- HR Team (Wave 4 для enterprise)

### Vertical-template lifecycle

- Каждая template имеет SemVer (1.0.0 + minor for prompt updates + major for breaking)
- Golden dataset per template: 30-50 эталонных задач + reference outputs
- Canary rollout (5% → 25% → 100%) при minor/major (ADR-010)

## Consequences

- Defensible moat: РФ-domain knowledge encoded в templates
- Marketing ICP-фокус: 5 чётких сегментов
- Workflow-DAG для каждой vertical встроен → wizard-clear UX
- ИП-Бухгалтерия — high-stakes, требует strictest disclaimers + approval mode

## Links

- Risks: [R-02](../risks/REGISTER.md), [R-10](../risks/REGISTER.md), [R-30](../risks/REGISTER.md)
- Phase: 00.5 (WB-Селлер), 01.1 (3 vertical W1), 02.2 (5 vertical W2)
- Related ADRs: ADR-016 (team-first UX), ADR-019 (vertical rituals), ADR-013 (MCP), ADR-010 (versioning)
