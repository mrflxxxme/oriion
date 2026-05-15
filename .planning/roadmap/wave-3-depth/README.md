# Wave 3 — Глубина + полный vertical-каталог (10 недель)

> **Revision 2026-05-15:** Wave 3 scope expanded — **+2 vertical-templates (ИП-Бухгалтерия + СМБ-Sales с Master-Agent)** graduated W2→W3 per Session-decision. Plus original Vertical Rituals + PARA Workspace + corp connectors. Timebox 8 → 10 weeks. See [Session-decision](../../JOURNAL.md).

## Цель волны

**General Availability (GA) релиз.** Полный каталог 6 templates (horizontal + 5 vertical), Vertical Rituals + «Знания команды» (PARA) активны, корпоративные коннекторы (1С / Эльба / Контур.Экстерн / Тинькофф Бизнес), autonomous mode для vertical-templates, полный аудит + Approval mode, Customer Success programme активна, Langfuse observability.

## Метрика успеха

- 500 платящих команд
- MRR ≥3 млн ₽
- Monthly churn <8%
- Все **6 templates** имеют active retention (1 horizontal + 5 vertical, Health Score green >70%)
- 3+ активных partner (внутренняя programme)
- NPS ≥30
- Vertical Rituals: используют >25% paid teams
- ИП-Бух + СМБ-Sales verticals (W3-new): ≥10 платящих команд per vertical к концу wave

## Критерий перехода к Wave 4

- ✅ Все phase'ы — Done
- ✅ GA-релиз публично объявлен
- ✅ MRR achieved
- ✅ Customer Success programme работает (CS-manager в штате)
- ✅ Partner-программа инфра готова (полноценный запуск — Wave 4)

## Scope

**Must:**
- **+2 vertical-templates (graduated W2→W3):** ИП-Бухгалтерия (1С/Эльба) + СМБ-Sales (Bitrix24/amoCRM) с Master-Agent layer (deep prompts в `contracts/role-prompts/masters/accounting-ip-master.md` + `smb-sales-master.md`)
- **2 hand-drawn vertical-героев:** «Бухгалтер-Анна» + «Sales-Дмитрий» (Pixel Department contribution)
- **Golden datasets** для ИП-Бух + СМБ-Sales (30-50 задач each)
- Vertical Rituals Catalog (per vertical-template, ADR-019) — Master-Agents становятся ritual-owners per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md) §«Wave 3 extension»
- «Знания команды» (PARA Workspace) — Проекты / Сферы / Ресурсы / Архив; Master-Agents читают PARA как primary domain-memory per ADR-011 + ADR-029
- Corporate MCP-серверы (наши): 1c-rest-mcp, kontur-elba-mcp, kontur-extern-mcp, tinkoff-business-mcp, **ozon-seller-mcp** (graduated с WB-Селлер vertical Wave 2 deferral)
- Расширение community MCP-каталога (20+ серверов)
- Workflow-шаблоны (сохранение и переиспользование процессов через DAG)
- Approval mode + полный immutable audit log (требуется ИП-Бух vertical — high-stakes)
- Telegram-бот для команды (нотификации + быстрые команды)
- Langfuse self-hosted + расширенный OpenTelemetry
- Customer Success programme: human CS, community Telegram-чат, Health Score-driven outreach
- Образовательный контент: 5 уроков на YouTube, 20+ use-case-страниц
- 2D-сцена офиса (полная, с anim transitions)
- (опц., если customer demand) Server-side gVisor sandbox для long-running Analyst

**Nice (опционально):**
- AI-Coach (PLG механика — Wave 3+ / Wave 4)
- Visual workflow editor — Wave 4
- Sertification programme для пользователей — Wave 4

## Длительность и команда

- **Срок:** 10 недель (revision 2026-05-15: +2 нед vs prior 8 weeks — поглощают +2 vertical-templates с Master-Agents + 2 hand-drawn героев + golden datasets)
- **Команда:** +Customer Success Manager, +Marketing Specialist; Tech Lead, Senior Backend, Middle Backend, Senior Frontend, DevOps 0.5, Designer
- **Бюджет AI-dev:** ~$7500 (corrected vs prior $6000 — +2 verticals)

## Phases

См. [PHASES.md](./PHASES.md).

> **⚠️ Phase-файлы Wave 3 — placeholder под прежнюю архитектуру.** Каждая phase регенерируется в начале Wave 3 на базе актуальных ADR + результатов Wave 2 retro.

## Risks specific

- **R-02 (high-stakes vendors):** lawyer/accountant получают первую серьёзную нагрузку — мониторим жалобы
- **R-04 (autonomous):** autonomous mode требует строгих лимитов, deadman switch
- **R-08:** РКН-проверка вероятна на growth-стадии, готовы к запросам
- **R-11 (churn):** Health Score must work, proactive outreach обязателен

## Артефакты к концу волны

- GA-продукт на production-домене
- MCP-каталог с 5–10 публичными MCP-серверами
- Workflow-шаблоны library
- Корпоративные коннекторы работают, audit'ы проходят
- Telegram-бот (бот для управления, не для атаки)
- Langfuse trace'ы и метрики full
- Community Telegram-чат >500 человек
- Vertical-2 landing + использование
- CS programme работает: 70%+ green Health Score
