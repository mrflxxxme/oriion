# ADR-017: Horizontal entry + 5 vertical-templates как primary USP

- **Status:** Accepted (revision: 2026-05-15 — horizontal preset added, vertical wave-distribution re-ordered)

## Decision

### Dual positioning per [Session-decision 2026-05-15](../JOURNAL.md)

Платформа стартует с **horizontal team-preset как entry-point** для всех пользователей; **vertical-templates** надстраиваются как «depth-presets» через Master-Agent layer per [ADR-029](./ADR-029-master-agent-vertical-templates.md).

### Catalog of team-presets (поэтапная выкатка)

| # | ID | Иконка | Name | Wave | Тип | Master-Agent |
|---|---|---|---|---|---|---|
| 0 | `productivity_core` | 🧰 | **Твои личные ассистенты** (horizontal) | W0 (anchor) | horizontal | — (Coordinator top-level) |
| 1 | `agency_marketing_ru` | 📈 | **Маркетинг-агентство РФ** | W1 | vertical | ✅ Master-Agent (ADR-029) |
| 2 | `telegram_creator` | ✍️ | **Telegram-крейтор / Курс-автор** | W1 | vertical | ✅ Master-Agent |
| 3 | `wb_seller_v1` | 🛒 | **WB-Селлер команда** | **W2 (graduated W0→W2)** | vertical | ✅ Master-Agent |
| 4 | `accounting_ip` | 💼 | **ИП-Бухгалтерия (1С/Эльба)** | **W3 (graduated W2→W3)** | vertical | ✅ Master-Agent |
| 5 | `smb_sales_ru` | 🎯 | **СМБ-Sales (Bitrix24/amoCRM)** | **W3 (graduated W2→W3)** | vertical | ✅ Master-Agent |

### Wave-distribution rationale

- **W0:** один horizontal preset для internal demo + USP validation. Demo-сценарий «Market & content brief» (3 артефакта, 4 роли). Полное описание — Wave 0 phase 00.5 spec.
- **W1:** 2 vertical-template над horizontal-baseline — Marketing-agency + Telegram-крейтор. Эти вертикали выбраны как «depth-presets, которые усиливают horizontal» (а не уходят в узкую нишу). Master-Agent layer впервые инстанциируется здесь.
- **W2:** WB-Селлер vertical (graduated из original W0 plan — теперь как primary vertical для public-beta). Plus Pixel Department, Pyodide, Telegram Mini App, Master-Agent retrofit Coordinator-API.
- **W3:** ИП-Бух + СМБ-Sales (graduated из W2). Plus Vertical Rituals, PARA Workspace, autonomous mode.

### Composition of horizontal preset (W0)

#### 0. Твои личные ассистенты (productivity_core, W0 horizontal anchor)

- **Целевой пользователь:** SMB + солопренёры + personal-users (общая продуктивность)
- **Agents (W0 — Coordinator + 3 specialists):**
  - Coordinator (deepseek-r1, name «Координатор») — top-level orchestrator per [ADR-022](./ADR-022-coordinator-wizard-llm-hybrid.md)
  - Researcher (deepseek-v3, name «Исследователь») — web_search + read_url
  - Writer (deepseek-v3, name «Копирайтер») — marketing/content/brief outputs
  - Analyst (deepseek-r1, name «Аналитик») — LLM-only Wave 0, Pyodide-augmented Wave 2 per [ADR-020](./ADR-020-pyodide-code-execution.md)
- **MCP-tools Wave 0:** built-in web_search + read_url only
- **Deep role prompts:** [contracts/role-prompts/](../contracts/role-prompts/) — coordinator.md + researcher.md + writer.md + analyst.md (9-section deep, first-draft в Phase 00.5; hardening pass в Phase 01.1 retro)
- **Demo сценарий W0:** «Market & content brief для нового продукта» — 3 артефакта (brief.md + competitive-matrix.md + content-plan.md)
- **Vertical rituals:** N/A (horizontal не имеет vertical-specific rituals)
- **Wave 1 extension:** Master-Agent НЕ добавляется (horizontal остаётся однослойным); roles получают conversation-history persistence (W1) + cell-memory hooks
- **Wave 2 extension:** Pyodide для Analyst
- **Wave 3 extension:** PARA-memory доступ ролям

### Composition per template

#### 3. WB-Селлер команда (W2 — graduated из original W0 plan)
- **Целевой клиент:** селлеры WildBerries (600K+ в РФ)
- **Agents (W2 — Master + Coordinator + specialists per [ADR-029](./ADR-029-master-agent-vertical-templates.md)):**
  - **Master-Agent «WB-Селлер CEO»** (deepseek-r1, vertical-knowledge keeper)
  - Coordinator (deepseek-r1, sprite formal01, name «Алексей») — operational COO
  - Listing Writer (deepseek-v3, sprite creative01, name «Марк») — WB-specific
  - Researcher (re-used из horizontal preset, vertical-overlay в context)
  - Analyst (re-used из horizontal preset с Pyodide capability к W2)
  - + W3: SMM (deepseek-v3, sprite creative04, name «Анастасия»)
- **Hand-drawn vertical-герой (W2):** «Селлер-Маркус»
- **Workflow steps:**
  1. Researcher: анализ топ-конкурентов по артикулу/нише
  2. Listing Writer: создаёт описание товара по результатам анализа
  3. Analyst (W1): анализ продаж + конверсии (через Pyodide CSV)
  4. SMM (W2): контент-план для Telegram-канала
- **MCP-tools (W2):** wb-partners-mcp, telegram-mcp v0.2 (Business API per [ADR-030](./ADR-030-telegram-business-api.md)), yandex-disk-mcp (ozon-seller-mcp — W3 along с ИП-Бух / СМБ-Sales)
- **Vertical rituals (W3):**
  - 06:00 daily: проверка цен топ-5 конкурентов
  - 09:00 mon-fri: dashboard продаж за вчера
  - mon 10:00: weekly sales report для owner
  - alert при падении конверсии артикула >10%

#### 1. Маркетинг-агентство РФ (W1 — vertical anchor for Wave 1)
- **Целевой клиент:** маркетинг-агентства (30K+)
- **Agents (W1 — Master + Coordinator + specialists per [ADR-029](./ADR-029-master-agent-vertical-templates.md)):**
  - **Master-Agent «Marketing-Agency CEO»** (deepseek-r1, vertical-knowledge keeper)
  - Coordinator (deepseek-r1, sprite formal02, name «Дмитрий») — operational COO, retrofit для subordinate-mode
  - Researcher (re-used из horizontal preset)
  - Writer (re-used из horizontal preset с vertical-overlay)
  - Designer (deepseek-v3, sprite creative05, name «Дизайнер») — vertical-specific
  - SMM (deepseek-v3, sprite creative04, name «Анастасия») — vertical-specific
  - Analyst (re-used; Pyodide-augmented с W2)
- **Hand-drawn vertical-герой (W2):** «SMM-Анастасия»
- **MCP-tools (W1):** telegram-mcp v0.2 (Business API per [ADR-030](./ADR-030-telegram-business-api.md)), yandex-disk-mcp, imap-smtp-mcp; (bitrix24-mcp / amocrm-mcp / gmail-mcp — W2)
- **Vertical rituals (W3):**
  - mon 09:00: weekly content-plan для клиентов
  - daily 18:00: monitoring trending тем в Telegram-каналах ниши клиентов
  - alert при появлении trending-темы → draft-пост
  - end-of-month: client report draft

#### 2. Telegram-крейтор / Курс-автор (W1 — second vertical for Wave 1)
- **Целевой клиент:** Telegram-каналы 50K+ авторов с monetization
- **Agents (W1 — Master + Coordinator + specialists per [ADR-029](./ADR-029-master-agent-vertical-templates.md)):**
  - **Master-Agent «Telegram-Creator CEO»** (deepseek-r1, vertical-knowledge keeper)
  - Coordinator (deepseek-r1, sprite formal04, name «Координатор») — operational COO
  - Writer (re-used из horizontal preset с TG-content-overlay)
  - Researcher (re-used из horizontal preset)
  - Marketer (deepseek-v3, sprite creative03, name «Маркетолог») — vertical-specific
  - Community-manager (deepseek-v3, sprite creative06, name «Сообщество») — vertical-specific, Business API consumer
- **Hand-drawn vertical-герой (W2):** «Крейтор-Денис»
- **MCP-tools (W1):** telegram-mcp v0.2 (Business API per [ADR-030](./ADR-030-telegram-business-api.md)) primary, yandex-disk-mcp; (gmail-mcp + getcourse-mcp — W3); (Telegram Mini App — W2)
- **Vertical rituals (W3):**
  - daily 10:00: контент-идеи на сегодня (1 пост + 1 stories)
  - weekly mon: analytics-отчёт за неделю
  - email-серия sales-funnel (auto-trigger при покупке)

#### 4. ИП-Бухгалтерия (W3 — graduated W2→W3) — HIGH-STAKES vertical
- **Целевой клиент:** ИП в РФ (3M+, ОСН/УСН/НПД)
- **Agents (W3 — Master + Coordinator + specialists, все с requires_human_approval=true для write-actions):**
  - **Master-Agent «Accountant CEO»** (deepseek-r1 + yandex-pro, vertical-knowledge keeper, regulatory-compliance enforcer)
  - Coordinator (deepseek-r1, sprite formal05, name «Координатор») — operational COO
  - Accountant (deepseek-r1 + yandex-pro, sprite formal02, name «Анна»)
  - Юрист (deepseek-r1, sprite formal03, name «Дмитрий»)
  - Reporter (re-used из horizontal preset с overlay)
- **Hand-drawn vertical-герой (W2):** «Бухгалтер-Анна»
- **MCP-tools (W3):** 1c-rest-mcp, kontur-elba-mcp, kontur-extern-mcp, tinkoff-business-mcp, gmail-mcp
- **Vertical rituals (W3):**
  - daily 09:00: проверка статусов налоговых платежей в Эльбе
  - 5 дней до deadline отчётности: reminder + check готовности данных
  - при новом письме от ФНС: extraction + analysis + draft-ответ
- **Safety:** disclaimer mandatory на каждый ответ, никакой autonomy для финансовых проводок, approval mode by default

#### 5. СМБ-Sales (W3 — graduated W2→W3)
- **Целевой клиент:** СМБ-компании с CRM (100K+)
- **Agents (W3 — Master + Coordinator + specialists per [ADR-029](./ADR-029-master-agent-vertical-templates.md)):**
  - **Master-Agent «Sales CEO»** (deepseek-r1, vertical-knowledge keeper)
  - Coordinator (deepseek-r1, sprite formal01, name «Координатор») — operational COO
  - Sales-manager (deepseek-v3, sprite creative01, name «Sales») — vertical-specific
  - Researcher (re-used из horizontal preset)
  - Writer (re-used из horizontal preset)
  - SMM (deepseek-v3, sprite creative04, name «SMM») — vertical-specific
- **Hand-drawn vertical-герой (W2):** «Sales-Дмитрий»
- **MCP-tools (W3):** bitrix24-mcp, amocrm-mcp, ozon-seller-mcp, telegram-mcp v0.2, gmail-mcp
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

- Defensible moat: РФ-domain knowledge encoded в Master-Agent prompts (ADR-029)
- Marketing dual-funnel: horizontal entry для broad-audience + vertical depth-presets для domain-buyers
- Master-Agent layer = primary differentiation для vertical-tier pricing
- 5 vertical-segments + 1 horizontal-segment в каталоге = 6 product surfaces
- ИП-Бухгалтерия — high-stakes, требует strictest disclaimers + approval mode + Master-Agent с regulatory-compliance focus

## Links

- Risks: [R-02](../risks/REGISTER.md), [R-10](../risks/REGISTER.md), [R-30](../risks/REGISTER.md)
- Phase: 00.5 (horizontal productivity-core), 01.1 (2 vertical W1 — Marketing + Telegram + Master-Agent first instances), 02.X (WB-Селлер vertical + Pixel + Mini App), 03.X (ИП-Бух + СМБ-Sales)
- Related ADRs: ADR-016 (team-first UX), [ADR-029](./ADR-029-master-agent-vertical-templates.md) (Master-Agent layer), [ADR-022](./ADR-022-coordinator-wizard-llm-hybrid.md) (Coordinator hybrid + horizontal vs vertical), ADR-019 (vertical rituals), [ADR-013](./ADR-013-mcp-protocol.md) (MCP — telegram-mcp v0.2 update), [ADR-030](./ADR-030-telegram-business-api.md) (Telegram Business API), ADR-010 (versioning)
