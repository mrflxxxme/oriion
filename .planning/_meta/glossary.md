# Glossary — единый словарь домена

> Не повторять определения в phase-файлах — ссылаться сюда.

## Сущности продукта

| Термин | Определение |
|---|---|
| **Workspace** | Аккаунт пользователя. Может содержать N **Cells** в зависимости от тарифа. Биллинг привязан к workspace. |
| **Cell** | **Активная AI-команда** в изолированном пространстве (логическая ячейка с дня 1, физическая — Wave 3+ опционально). Cell = team workspace с дедицированными данными, secrets, audit, runtime. Имеет cell_id, region, status, plan_tier, llm_config, stack_preference. См. ADR-009. |
| **Team-preset** | Готовый шаблон команды для hire (e.g. «WB-Селлер команда», «Маркетинг-агентство РФ»). Содержит pre-bundled набор агентов + workflow DAG. 5 стартовых vertical-templates. Team-preset = first-class unit в team-first UX. См. ADR-016, ADR-017. |
| **Vertical-template** | Синоним team-preset для vertical-specific шаблонов (5 стартовых). Включает: РФ-domain prompts, vertical MCP-серверы, vertical rituals. |
| **Agent** | Конкретный AI-сотрудник в cell. Имеет sprite, имя (Марк, Анна, ...), внутреннюю role-метадату (researcher / writer / analyst / ...), system_prompt, default_tools. AI employee = 1 agent = 1 слот в тарифе. |
| **Role** | **Внутренняя метадата агента** (не user-facing unit). 11 ролей: coordinator, researcher, writer, analyst, dev, designer, manager, accountant, lawyer, smm, sales. |
| **Coordinator** | Системный агент (всегда есть в cell): на free-tier = wizard (3 шага), на trial/paid = LLM-driven (DeepSeek-V3/R1). Vertical-aware prompts. Decomposes user tasks → assigns sub-tasks правильным агентам. См. ADR-022. |
| **Task** | Атомарная единица работы agent'а. Привязана к user, agent, cell. Имеет статус, цену в кредитах, artifacts. |
| **Sub-task** | Часть decomposed task, выполняется одним конкретным agent'ом по плану Coordinator'а. |
| **Artifact** | Результат работы agent'а: документ (Yjs), код, изображение, отчёт. Citeable URL `artifact://<id>`. Версионируется или иммутабельный (S3). См. ADR-012. |
| **Cell memory** | Общая память cell (фактoложcommands, документы, glossary). Доступна всем агентам через RAG. См. ADR-011. |
| **Role memory** | Личная память agent-instance: предпочтения, стилевые/процессные паттерны. |
| **Знания команды** | Wave 3+ структурированная knowledge base per cell: **Проекты / Сферы / Ресурсы / Архив**. См. ADR-011, ADR-019. |
| **Vertical Ritual** | Pre-baked autonomous ритуал per vertical-template (cron + prompt + action). E.g. «WB-Селлер: проверка цен конкурентов в 06:00 daily». Wave 3+. См. ADR-019. |
| **Outcome Profile** | Preset плотности autonomy: «Тихий помощник» / «Активная команда» / «Я делегирую всё» / Custom. Wave 3+. |
| **Workflow template** | Сохранённый process: «задача → Researcher → Writer → Designer». Запускается повторно. Visual editor — Wave 4+. |
| **Pixel Department** | UI-метафора: pixel-art аватары агентов с анимациями. Реализация: Native HTML Canvas 2D + PNG sprite-sheets. AI-generated baseline + 5 vertical-героев hand-drawn (РФ-стилистика). Secondary USP. См. ADR-004, ADR-021. |
| **Vertical-герой** | Hand-drawn pixel-art персонаж, signature для конкретной vertical-template. 5 стартовых: Селлер-Маркус, SMM-Анастасия, Крейтор-Денис, Бухгалтер-Анна, Sales-Дмитрий. См. ADR-021. |

## Биллинг

| Термин | Определение |
|---|---|
| **Team-кредит** (T$ или Team-credit) | Внутренняя единица потребления. НЕ электронные деньги (юр.предосторожность). Wave 0: единый курс 1× для всех LLM-провайдеров (DeepSeek + RU). Wave 2+ при добавлении Anthropic/OpenAI через прокси: двухставочный (3× для Western стека). |
| **RU-стек** | LLM-провайдеры РФ-уровня: GigaChat (Сбер), YandexGPT (Yandex). |
| **China-стек** (premium) | DeepSeek-V3, DeepSeek-R1. Прямой API из РФ без VPN. |
| **Western-стек** (Wave 2+) | Anthropic Claude, OpenAI GPT через прокси-посредников. Только BYOK preferred. |
| **BYOK** (Bring Your Own Key) | Клиент использует свой API-ключ провайдера. Платформа берёт только subscription-fee (-80% от full credit cost). 9 провайдеров: deepseek, yandex, gigachat, openai, anthropic, google, openrouter, brave, exa. |
| **Soft-cap / Hard-cap** | Soft = уведомление при превышении. Hard = блокировка новых задач, требование явного opt-in. |
| **Overage** | Дополнительные кредиты сверх hard-cap. |
| **Trial** | 14 дней + 500 кредитов без привязки карты. См. ADR-022 (credit-limit guardrail). |

## Безопасность и compliance

| Термин | Определение |
|---|---|
| **High-stakes роли** | Lawyer, Accountant, Dev: требуют human-in-the-loop, имеют `requires_human_approval: true`. ИП-Бухгалтерия template — все агенты в approval mode. |
| **Domain scope / blacklist** | Whitelist/blacklist задач для role. Если задача вне scope — отказ + предложение живого специалиста. |
| **DLP-сканер** | Output-классификатор: блокирует/маскирует ПДн, банковские реквизиты, медицинские данные перед отправкой/сохранением. |
| **Approval mode** | Режим role: все tool-calls требуют подтверждения пользователя. Включаемо per role. |
| **Audit log** | Immutable append-only лог всех действий agents и доступов к ПДн. Retention 3 года (ФЗ-152). |
| **RBAC уровни** | Owner / Admin / Member / Viewer / Bot — per workspace. |
| **JIT-доступ** | Just-in-time доступ команды разработки к prod: запрос → одобрение → токен на 4ч → автоотзыв → лог сессии. |
| **Cell isolation** | Логическая изоляция cells: per-cell schema в Postgres, per-cell secrets в Lockbox, per-cell network whitelist, per-task sandbox-context (Pyodide или MCP-server). |

## Уровни деградации сервиса

| Уровень | Триггер | Что отключается |
|---|---|---|
| **Green** | norm | Всё работает |
| **Yellow** | queue >1000 или p95 >5s | Autonomous mode пауза, golden dataset stop, batched notifications |
| **Orange** | queue >5000 или error >10% | Pixel в polling, агрессивный cache MCP, trial throttle |
| **Red** | queue >20000 или провайдер down | Trial registrations closed, баннер, focus на paid |

## Стратегические термины

| Термин | Определение |
|---|---|
| **Health Score** | Метрика клиентского здоровья: Green (80+) / Yellow (50–79) / Red (<50). Триггер proactive outreach. |
| **TTFV** | Time To First Value: время от регистрации до первого собственного артефакта. Цель: <3 мин. |
| **ICE score** | (Impact × Strategic × Risk) / Effort. ≥5 — high priority. |
| **Kill criteria** | Заранее заданный сигнал «закрываем стратегическую ставку». См. risks/REGISTER.md. |
| **Wave** | Релизный цикл с самостоятельной ценностью (3–12 нед). 6 волн (0–5+). |
| **Phase** | Атомарная фаза внутри волны. Имеет dependencies, tasks, acceptance criteria. |

## Технические термины

| Термин | Определение |
|---|---|
| **MCP-сервер** | Model Context Protocol — open standard для connector tools. Каждая интеграция (Bitrix24, WB Партнёры, и т.д.) = отдельный MCP-сервер. Pydantic-AI поддерживает MCP-клиента нативно. См. ADR-013. |
| **Pyodide** | Python WebAssembly runtime в браузере. Используем для Analyst-роли в Wave 2. См. ADR-020. |
| **Pixel-Art-XL LoRA** | Community model для SDXL/Flux, генерирует pixel-art стиль. Используется в asset-pipeline Wave 2 (ADR-021). |
| **Aseprite** | Pixel-art редактор. Используется для post-processing AI-generated assets. |

## Схема данных (термины из контрактов)

> Канонические identifier'ы из `contracts/<bounded-context>/` per [ADR-024 §2](../decisions/ADR-024-bounded-context-contracts.md#2-naming-corrections). При работе с DDL/migrations использовать ТОЛЬКО эти термины.

| Термин | Определение |
|---|---|
| **agent_archetype** | Тип / шаблон агента из таблицы `agents.agent_archetypes` (pre-defined): хранит system_prompt, default_tools, recommended_model_tier, UI sprite reference. 24 стартовых архетипа (5 vertical-героев + 19 generic). См. [ADR-024 §2](../decisions/ADR-024-bounded-context-contracts.md#2-naming-corrections), [ADR-021](../decisions/ADR-021-ai-generated-pixel-pipeline.md). Deprecated alias: `ui_sprite_archetype` (никогда не использовать в новых implementations per [P-AUDIT-2](../decisions/ADR-028-policies-registry.md#policies-canonical-home)). |
| **agent_archetype_id** | FK к `agents.agent_archetypes.archetype_id`. Используется в `agents.roles`, `agents.team_presets`, `agents.cell_agents`. **Никогда** не использовать deprecated `ui_sprite_archetype` / `sprite_id` в новом коде. См. [ADR-024 §2](../decisions/ADR-024-bounded-context-contracts.md#2-naming-corrections). |
| **system_role** | Запись в `rbac.system_roles` (system-level permissions: Owner / Admin / Member / Viewer / Bot per workspace). **НЕ путать** с `agent_archetype` (vertical-level AI agent role) или с `agents.roles` (внутренняя role-метадата agent'а). См. [ADR-024 §2](../decisions/ADR-024-bounded-context-contracts.md#2-naming-corrections). Deprecated alias: `roles_rbac` (renamed per ADR-024). |
