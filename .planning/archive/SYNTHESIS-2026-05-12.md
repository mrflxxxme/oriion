# SYNTHESIS — пересмотр roadmap после анализа teamly.to

> **Дата:** 2026-05-12
> **Цель:** консолидировать 12 решений grill-me-интервью в actionable change-list для roadmap, ADR и risks-register.
> **Триггер:** анализ teamly.to + приоритеты founder'а (простота, скорость MVP, AI-friendly, РФ-killer, глобальные коннекторы доступны).

---

## Карта 12 принятых решений

| # | Развилка | Решение | Главное последствие |
|---|---|---|---|
| Q1 | Team-first vs Role-first | **Team-first UX в MVP, role-swap в Wave 3+** | Wave 0-1 сильно проще, mental model для СМБ ясный |
| Q2 | Pixel Department vs РФ-эксперт | **РФ-вертикальная экспертиза — primary USP** | Pixel остаётся secondary, маркетинг переориентирован |
| Q3 | Cell isolation | **Логические cells на shared physical с дня 1**, physical cells опционально Wave 3 | Cell как domain concept с Wave 0 |
| Q4 | LLM-стек | **DeepSeek-V3/R1 (Premium) + YandexGPT + GigaChat в Wave 0**, BYOK для всех 3 | Без VPN, без зарубежного юр в Wave 0 |
| Q5 | Коннекторы | **MCP-протокол с Wave 0 + кураторский каталог**, Composio НЕ используем | Открытая архитектура, no vendor lock-in |
| Q6 | Autonomous mode | **Vertical-rituals + core Wave 2 + PARA (Знания команды) Wave 3** | Vertical-specific killer-функционал |
| Q7 | Frontend | **Vite 6 + React 19 + TanStack Router + FastAPI отдельно** | Простота, AI-agent-friendly, 40% меньше bundle |
| Q8 | Auth | **Custom JWT Wave 0-1, Logto self-hosted Wave 2-3, Keycloak только Enterprise** | -3 дня в Wave 0 |
| Q9 | Pixel assets | **AI-generated baseline (24 archetypes) + 5 vertical-героев hand-drawn + РФ-стилистика** | $3-5K vs $25K |
| Q10 | Coordinator на free | **Wizard на landing + LLM-Coordinator для trial/paid**, vertical-aware prompts | TTFV <3 мин |
| Q11 | Code sandbox | **Pyodide WASM в браузере для Analyst (Wave 2)**, server-side gVisor опционально Wave 3+ | $0 backend infra, ФЗ-152-friendly |
| Q12 | Стартовые vertical-templates | **5 templates: WB-Селлер, Маркетинг-агентство, Telegram-крейтор, ИП-Бухгалтерия, СМБ-Sales** | Поэтапная выкатка W0→W2 |

---

## Что обновляется в `.planning/`

### A. ADR-файлы — переписать/обновить

| ADR | Действие | Что меняется |
|---|---|---|
| **ADR-001** (modular monolith) | Обновить | Frontend = **Vite + React 19 + TanStack Router** (не Next.js 15). Backend = FastAPI (без изменений). Marketing-site = Astro 5 (отдельный трек Wave 2). |
| **ADR-002** (LLM gateway) | Переписать | **Триконтурный стек:** China (DeepSeek) + RU (YandexGPT/GigaChat) + Western (Wave 2+ через прокси). BYOK first-class с дня 1 для 3 провайдеров. Двухставочный курс — только когда добавим Western proxy. |
| **ADR-004** (Pixel Department) | Переписать | **Native Canvas 2D** (НЕ PixiJS) + PNG sprite-sheets + CSS pixelBob. Pixel = secondary USP. РФ-стилистика. AI-generated baseline. |
| **ADR-006** (sandbox) | Переписать | **Pyodide WASM в браузере** для Wave 2 (Analyst). Server-side gVisor — Wave 3+ опционально. Firecracker — Wave 5+. |
| **ADR-007** (auth) | Переписать | **Custom JWT** (FastAPI + bcrypt + Redis) Wave 0-1. **Logto self-hosted** Wave 2-3. **Keycloak** только Enterprise Wave 4+. |
| **ADR-009** (multitenancy) | Обновить | Уровень **B+ (логические cells)** добавляется как стартовый. **Cell** = first-class domain concept с Wave 0. Physical cells — Wave 3+ опционально. |
| **ADR-011** (memory) | Обновить | **Persistent memory в Wave 2** (не Wave 5+ как было). **PARA Workspace = «Знания команды»** в Wave 3. Episodic memory — нужна для autonomous-режима. |
| **ADR-013** (MCP) | Переместить с Wave 3 на **Wave 0** | MCP-клиент в Pydantic-AI runtime с дня 1. Кураторский каталог. Composio НЕ используем (опциональный bridge Wave 3-4). |

### B. Новые ADR — создать

| Новый ADR | Тема |
|---|---|
| **ADR-016** | Team-first UX (Q1) — преимущество перед role-first |
| **ADR-017** | Vertical-templates как primary USP (Q2 + Q12) — список 5 стартовых |
| **ADR-018** | DeepSeek как primary LLM-стек (Q4) — рационализация выбора над Anthropic |
| **ADR-019** | Vertical-specific Autonomous Mode (Q6) — отличие от teamly's PARA |
| **ADR-020** | Pyodide WASM для code-execution (Q11) — обоснование над server-side sandbox |
| **ADR-021** | AI-generated pixel-assets pipeline (Q9) — рационализация бюджета |
| **ADR-022** | Coordinator: Wizard + LLM hybrid (Q10) — двухконтурная стратегия |

### C. Wave-файлы — обновить

#### Wave 0 (Foundation)

**Бывшая цель:** Internal demo: 1 роль (Writer) → текстовый ответ

**Новая цель:** Internal demo: **WB-Селлер team-preset** (3 агента — Coordinator + Listing Writer + Researcher) end-to-end через DeepSeek + YandexGPT + GigaChat (BYOK), задача → workflow → artifact.

Phase-changes:
- **Phase 00.1** (repo + CI): убрать Authentik из Docker Compose, добавить Vite scaffold
- **Phase 00.2** (Authentik): **переименовать в «Custom auth (JWT + bcrypt + Redis)»**, 1-2 дня вместо 3-5
- **Phase 00.3** (DB+RLS): **обновить под Cell-aware schema** (cell_id вместо workspace_id, схема per team)
- **Phase 00.4** (LLM-gateway): **3 LLM-провайдера (DeepSeek + YandexGPT + GigaChat)** с BYOK-режимом + **MCP-клиент infrastructure**
- **Phase 00.5** (Pydantic-AI + Writer): **переписать как «WB-Селлер team-preset»** с 3 агентами и hardcoded workflow
- **Phase 00.6** (deploy): без изменений

#### Wave 1 (Core MVP)

**Бывшая цель:** 3 роли + memory + artifacts + billing + RBAC + Claude через прокси

**Новая цель:** Pre-alpha для friends: **3 vertical-templates** (WB-Селлер + Маркетинг-агентство + Telegram-крейтор) + persistent memory + artifacts + billing + RBAC + расширение BYOK до 5 LLM.

Phase-changes:
- **Phase 01.1** (Coordinator + Researcher): **расширить до 3 vertical-templates** с domain-aware prompts
- **Phase 01.2** (memory): **persistent memory across sessions** добавляется (extend для autonomy подготовки)
- **Phase 01.3** (artifacts): без изменений
- **Phase 01.4** (billing): **+ BYOK-tariff с отдельной шкалой** (managed vs BYOK)
- **Phase 01.5** (dashboard UI): **переписать под Vite + TanStack** + добавить Coordinator-wizard на landing
- **Phase 01.6** (security): без изменений
- **Phase 01.7** (RBAC): без изменений
- **Phase 01.8** (Claude proxy): **перенести с Wave 1 на Wave 2** — DeepSeek закрывает primary need
- **Phase 01.9** (onboarding): **переписать с wizard на landing + auto-spawn trial-cell с pre-selected vertical-team**

#### Wave 2 (Pixel + полный каталог)

**Бывшая цель:** Public beta — Pixel + 11 ролей + gVisor + 4 коннектора + 6 пресетов

**Новая цель:** Public beta — **5 vertical-templates** + Pixel Department (AI-generated + 5 hand-drawn героев) + Pyodide для Analyst + расширенный MCP-каталог (15+ серверов: 5 РФ-killer + 10+ community) + **core autonomy infrastructure** (memory + cron + heartbeat).

Phase-changes:
- **Phase 02.1** (Pixel Department): **переписать на Native Canvas 2D + AI-generated baseline + 5 vertical-героев** (бюджет $3-5K)
- **Phase 02.2** (11 ролей): **переписать как «10+ team-presets»** + Wave 2 расширяет 3 vertical → 5 vertical (+ ИП-Бухгалтерия + СМБ-Sales) + generic-presets
- **Phase 02.3** (gVisor + Dev role): **переписать как «Pyodide для Analyst»** (3 дня, 0 backend)
- **Phase 02.4** (connectors): **переписать как «MCP-серверы для 5 РФ-killer-коннекторов»** (Telegram, Yandex.Disk, Bitrix24, amoCRM, WB Партнёры)
- **Phase 02.5** (onboarding full): **6 пресет-команд → 5 vertical-templates с fake-history + live demo task**
- **Phase 02.6** (RBAC full): без изменений
- **Phase 02.7** (Vertical-Marketing): **сливается в Phase 02.2** (vertical с дня 1, не отдельная фаза)
- **Phase 02.8** (golden datasets): **per-vertical golden datasets** вместо per-role
- **Новая Phase 02.9**: **Core Autonomy infrastructure** (persistent memory + cron + heartbeat — подготовка к Wave 3 rituals)

#### Wave 3 (Глубина)

**Бывшая цель:** MCP + workflows + corp connectors + autonomous mode + customer success + vertical-2 (e-commerce)

**Новая цель:** GA — **Vertical Rituals Catalog (per-template)** + PARA Workspace («Знания команды») + workflows + расширенный connector-каталог (Ozon Seller, 1С REST, Эльба, Контур.Экстерн) + customer success + generic-presets каталог расширяется до 8 templates.

Phase-changes:
- **Phase 03.1** (MCP): **переносится в Wave 0** (Q5) — здесь только расширение catalog
- **Phase 03.2** (workflow templates): без изменений
- **Phase 03.3** (corp connectors): **переписать как MCP-серверы для Ozon Seller + 1С REST + Эльба + Контур.Экстерн**
- **Phase 03.4** (autonomous mode): **переписать как «Vertical Rituals Catalog»** + PARA Workspace («Знания команды») + 3 Outcome Profiles
- **Phase 03.5** (audit + approval): без изменений
- **Phase 03.6** (Telegram bot): без изменений
- **Phase 03.7** (Langfuse): без изменений
- **Phase 03.8** (customer success): без изменений
- **Phase 03.9** (vertical-2 e-commerce): **сливается в Phase 02.2** (включено в Wave 2 как WB-Селлер + Ozon Seller в Wave 3 как добавление)
- **Новая Phase 03.10**: **Generic team-presets каталог** (Content marketing, Sales-generic, HR-команда — без vertical-привязки)

#### Wave 4 (Scale + Partner)

**Без существенных изменений в scope**. Добавления:
- **Phase 04.x новая**: Physical cells (dedicated k8s namespace per Pro-tenant) — это Уровень C из ADR-009 (бывшая Phase 04.4 расширяется)
- **Phase 04.11**: **Server-side gVisor sandbox** — если в Wave 3 появился customer demand на Dev team с code execution
- **Phase 04.12**: **Migration с custom JWT на Logto self-hosted**

#### Wave 5+ (Enterprise & v2)

Без изменений по списку фаз, корректировки:
- Composio bridge (опциональный) — здесь, не Wave 4
- Открытый MCP-marketplace — здесь
- Firecracker microVMs — здесь
- ФСТЭК-сертификация — здесь при наличии gov-клиента

### D. Reference-файлы — обновить

| Файл | Что меняется |
|---|---|
| `_meta/stack.md` | Frontend: Vite+React+TanStack (не Next.js); Auth: Custom JWT (не Authentik); LLM: DeepSeek+YandexGPT+GigaChat (не Anthropic); 2D: Native Canvas (не PixiJS); Sandbox: Pyodide WASM (не gVisor MVP); MCP с Wave 0 |
| `_meta/glossary.md` | + **Cell** (domain concept, dedicated team workspace); + **Vertical-template** vs role; + **Vertical Rituals**; + **Знания команды (PARA)**; + **BYOK** определение; + **Wizard** vs Coordinator-LLM |
| `_meta/conventions.md` | Без существенных изменений |
| `_meta/open-questions.md` | Закрываются: OQ-01 (зарубежное юр на Wave 0), OQ-06 (прокси на Wave 0), OQ-07 (RU-провайдер). Появляются: OQ-25 (поиск freelance pixel-artist для 5 vertical-героев), OQ-26 (PoCs MCP-серверов для РФ-API) |
| `PROJECT.md` | Обновить wave-метрики; обновить current-status; обновить ключевой ADR-индекс |

### E. Risks-register — обновления

Добавлены в синтез (R-13...R-30, 18 новых рисков):

| ID | Источник | Severity |
|---|---|---|
| R-13 | Q5 (Composio dependency — снимается через MCP) | low (снят) |
| R-14 | Q9 (Pixel-art bottleneck — снижается через AI-generation) | medium → low |
| R-15 | Q5 (Composio санкционный risk — снимается) | low (снят) |
| R-16 | Q4 (BYOK ARPU pressure) | medium |
| R-17 | Q4 (Anthropic TOS — borrowed accounts) | medium |
| R-18 | Q5 (Open-source MCP-servers maintenance) | low |
| R-19 | Q6 (Autonomous mode legal consent) | medium |
| R-20 | Q6 (РФ-API stability for rituals) | medium |
| R-21 | Q8 (Custom auth security ownership) | medium |
| R-22 | Q8 (Auth migration vulnerability window) | low |
| R-23 | Q9 (AI-generated assets copyright) | low |
| R-24 | Q9 (Visual consistency) | low |
| R-25 | Q10 (Trial abuse) | medium |
| R-26 | Q10 (Trial-cell provisioning cost) | medium |
| R-27 | Q11 (Pyodide compatibility) | low |
| R-28 | Q11 (Client device weakness) | medium |
| R-29 | Q12 (Domain expert per vertical) | high — критично |
| R-30 | Q12 (WB/Ozon API breaking changes) | medium |

---

## Ключевые метрики по обновлённой стратегии

### Скорость MVP

| Параметр | Было | Стало | Дельта |
|---|---|---|---|
| **Wave 0 time** | 4 нед | **3 нед** | -25% |
| Phase 00.2 (auth) | 4 дня | 1-2 дня | -50% |
| Phase 00.4 (LLM) | 5 дней | 5 дней | = |
| Phase 00.5 (runtime) | 4 дня | 5 дней | +25% (team-preset вместо одной роли) |
| **Wave 0-1 total time** | 10 нед | **9 нед** | -10% |
| **Wave 2 budget Pixel** | $25K+ | **$3-5K** | -80% |
| **Wave 2 sandbox budget** | $50-100/mo + 8 days | **$0 + 3 days** | -100% |
| Wave 0-3 backend services | Authentik + Postgres + Redis | **Postgres + Redis** (без Authentik) | -1 service |

### Архитектурная сложность

- **Меньше services в Docker Compose** (нет Authentik, нет PixiJS-build pipeline complexity)
- **Один LLM-стек без VPN** в Wave 0 (DeepSeek + YandexGPT + GigaChat)
- **Native Canvas вместо PixiJS** (-500KB bundle)
- **Vite вместо Next.js** (быстрее dev-loop, проще mental model для AI-agents)
- **Pyodide вместо server-side sandbox** (0 backend ops для Wave 2)
- **MCP-стандарт вместо custom connector framework** (open ecosystem)

### РФ-killer-функционал (наши уникальные wedges)

1. **5 vertical-templates с дня 1** (WB / Маркетинг / Telegram / Бухгалтерия / Sales)
2. **РФ-LLM-стек без VPN** (YandexGPT, GigaChat, DeepSeek)
3. **РФ-MCP-серверы** (Telegram, Yandex.Disk, Bitrix24, amoCRM, WB, Ozon, 1С, Эльба)
4. **Vertical Rituals** (per-template autonomy сценарии под РФ-business)
5. **РФ-стилизованный Pixel Department** (5 hand-drawn vertical-героев)
6. **ФЗ-152 compliance с дня 1** (РФ-локализация ПДн, Yandex Cloud)
7. **Custom JWT auth с РФ-юр-связкой** (ООО + ИП biling association)
8. **Domain-aware Coordinator** для каждой vertical (terminology, workflow)
9. **₽-pricing с прозрачным BYOK** (-35% от managed)
10. **Pyodide-based аналитика без покидания клиентского браузера** (юр.compliance bonus)

### Глобальные коннекторы (сохранены)

Через MCP-протокол (open ecosystem):
- GitHub, GitLab — community MCP-servers
- Notion, Linear, Asana — community MCP-servers
- Slack, Discord — community MCP-servers
- Gmail, Google Drive, Google Sheets — community MCP-servers
- HubSpot, Salesforce — community MCP-servers
- Anthropic Claude / OpenAI GPT — через Wave 2 BYOK расширение
- Composio bridge — опционально Wave 3-4 для power-users с Composio account

---

## Что НЕ меняется (стабильные решения)

- **Backend Python 3.12 + FastAPI + asyncio + Pydantic-AI** (ADR-001, ADR-003)
- **PostgreSQL 16 + pgvector** (ADR-005)
- **Yandex Object Storage S3-совместимый** (ADR-012)
- **ЮKassa для billing** (ADR-008)
- **Yjs CRDT для документов** (ADR-012)
- **Audit log + RBAC + DLP** (ADR-014)
- **AI-dev process: 6 ролей + tier-based ревью** (ADR-015)
- **Risks-register структура** + quarterly review
- **Open-questions structure** (для founder-decisions)

---

## Финальный «sanity check»

**Соответствие приоритетам founder'а:**

1. ✅ **Простота, надёжность, актуальность с дня 1** — Vite+React+FastAPI+DeepSeek — современный стек 2026, AI-agent-friendly, без legacy. Logтelle/Keycloak — managed-стайл если потребуется.

2. ✅ **Максимально быстрый MVP на РФ-рынок** — 9 недель Wave 0+1 вместо 10. Стартуем с 1 РФ-vertical (WB-Селлер) day-1. Без VPN. Без зарубежного юр.лица в Wave 0.

3. ✅ **Простота поддержки и доработки** — Native Canvas vs PixiJS, Pyodide vs sandbox-pool, MCP vs custom framework, custom JWT vs Authentik. Каждое решение упрощает code-base.

4. ✅ **Понятность для AI-агентов** — Vite + React + TanStack + FastAPI = тривиальная связка, AI-agents знают наизусть. MCP — стандарт. Pydantic-AI знают хорошо. Tailwind+shadcn — стандарт. Никакого «новое и редкое».

5. ✅ **РФ-killer-фичи с сохранением глобальных коннекторов** — 5 vertical-templates + РФ-API + Vertical Rituals + РФ-стилистика. Глобальные коннекторы через MCP community-серверы + опциональный Composio bridge.

---

## Action items — next steps

1. **Tech Lead** (срочно): прочитать SYNTHESIS целиком, согласовать с founder, начать обновление ADR-001/002/004/006/007/009/011/013
2. **Founder + Tech Lead**: создать 7 новых ADR (ADR-016 — ADR-022)
3. **Tech Lead**: обновить wave-файлы Wave 0/1/2/3 phase-by-phase
4. **Founder**: закрыть OQ-25 (pixel-artist) + OQ-26 (PoC MCP-серверов) перед Wave 2
5. **DevOps**: подготовить environment для DeepSeek API + YandexGPT SDK + GigaChat SDK в Wave 0
6. **Senior Backend**: PoC Pyodide в браузере (~1 день) до Phase 02.3
7. **Senior Frontend**: PoC Vite + TanStack Router skeleton (~1 день) до Phase 00.1
8. **Founder**: 10+ customer-interviews per vertical (WB-Селлер, Маркетинг-агентство, Telegram-крейтор) ДО Wave 1 — для R-29 mitigation

---

## Готовность к Wave 0 старту

**Pre-requirements:**
- ✅ Roadmap пересмотрен (этот документ)
- ⚠️ ADR-файлы требуют обновления (8 existing + 7 new = 15 файлов)
- ⚠️ Wave-файлы требуют обновления (Wave 0-3 phase rewriting)
- ⚠️ OQ-25 (pixel-artist) — не решён, не blocker до Wave 2
- ⚠️ OQ-26 (PoC MCP-серверов) — не решён, желателен до Wave 2
- ⚠️ Customer-interviews (R-29) — пока не начаты, blocker до Wave 1

**Когда стартовать Wave 0:** после обновления ADR-001/002/004/006/007/008/009/011/013 + Phase 00.1-00.6 описаний (~3-5 рабочих дней работы). Customer-interviews идут параллельно.

**Целевая дата начала Wave 0:** **2026-05-19** (через неделю с момента synthesis) при условии быстрого обновления документов.

---

## Конец синтеза

Все 12 ключевых решений зафиксированы. Roadmap готов к технической peer-review командой и обновлению `.planning/` файлов. Следующая стадия — **техническая ревизия ADR** + **обновление wave-файлов** для готовности к старту Wave 0.
