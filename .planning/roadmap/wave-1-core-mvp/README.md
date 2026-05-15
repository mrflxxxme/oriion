# Wave 1 — Core MVP (6 недель)

> **Revision 2026-05-15:** Wave 1 scope changed: горизонталь (`productivity-core` из W0) + **2 vertical-templates** (Маркетинг-агентство РФ + Telegram-крейтор) с первой инстанциацией Master-Agent layer per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md). WB-Селлер vertical переезжает в Wave 2. Plus Telegram Business API per [ADR-030](../../decisions/ADR-030-telegram-business-api.md). See [Session-decision](../../JOURNAL.md).

## Цель волны

**Pre-alpha релиз для 10-15 friends-клиентов.** Ядро продукта (без Pixel Department) функционально: 1 horizontal + 2 vertical-templates выполняют полезные задачи, Master-Agent layer для verticals работает, Coordinator retrofit под subordinate-mode завершён, Telegram Business API даёт DM-killer-feature, биллинг считает, безопасность блокирует базовые векторы.

## Метрика успеха

- 10-15 friends-клиентов поставили ≥3 задачи каждый
- Task success rate ≥75%
- **3 templates работают:** `productivity-core` (horizontal) + Маркетинг-агентство РФ + Telegram-крейтор (verticals с Master-Agent)
- Telegram Business API: ≥3 friend-аккаунта подключили Business-bot для DM-management; consent flow validated
- Билинг записывает корректные транзакции
- Нет утечек cross-tenant (security audit)
- TTFV ≤5 мин для friends (target ≤3 мин — Wave 2 с full onboarding)

## Критерий перехода к Wave 2

- Все phase'ы Wave 1 — Done
- 10+ friends дали feedback, ключевые баги пофикшены
- Метрики успеха достигнуты
- Retro + risks register update проведены

## Scope

**Must:**
- Расширение каталога: **+2 vertical-templates** (Маркетинг-агентство РФ + Telegram-крейтор) поверх horizontal `productivity-core` из W0
- **Master-Agent layer first instantiation** per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md): MasterAgent base class + 2 vertical Masters (Marketing-agency + Telegram-creator) + deep Master-prompts в `contracts/role-prompts/masters/`
- **Coordinator API retrofit** под subordinate-mode (strategic_context input + Master-friendly output)
- **Role-prompts hardening pass** для horizontal preset (Phase 01.1 retro deliverable): прохождение по 4 horizontal-role-prompt-ам на основе internal demo replicate-failures
- Memory: cell + role (двухуровневая, manual control) — ADR-011 Wave 1 stage
- Persistent conversation history per agent (FIFO + summarization)
- Артефакты: документы Yjs + S3 для ассетов (ADR-012)
- Биллинг: T-кредиты + ЮKassa + Trial 14 дней + Solo тариф + BYOK режим (ADR-008)
- Dashboard UI (Vite + React + TanStack Router, без Pixel) — ADR-001
- Безопасность: input/output фильтр + capability sandboxing для dangerous tools (ADR-014)
- RBAC: Owner + Member (Admin + Viewer — Wave 2)
- LLM-gateway расширение: 2FA TOTP, magic-link, Yandex ID + VK ID OAuth
- **MCP-серверы (наши) — Wave 1 set:** telegram-mcp **v0.2 (Read + post + Business API)** per [ADR-030](../../decisions/ADR-030-telegram-business-api.md), yandex-disk-mcp, imap-smtp-mcp
- **Telegram Business API consent flow + privacy compliance** (152-ФЗ disclosure + РКН-уведомление update)
- Onboarding wizard (3 шага) для landing — конвертит в trial-cell с routing (horizontal vs vertical)
- 1 demo-сценарий per template для wow-эффекта (horizontal: Market & content brief; Marketing-agency: client campaign plan; Telegram-creator: content calendar + DM-funnel-analytics)

**Nice (можно отложить в Wave 2):**
- WB-Селлер vertical-template (moved W0 → W2 per Session-2026-05-15)
- Telegram Mini App (Wave 2)
- Telegram-бот для нотификаций (без команд)
- Promo codes
- Full Admin/Viewer RBAC
- Pixel Department (явно Wave 2)
- Anthropic/OpenAI через прокси (Wave 2+ при customer demand)

## Длительность и команда

- **Срок:** 6 недель
- **Команда:** Tech Lead, Senior Backend, Senior Frontend (старт), DevOps 0.5

## Phases

См. [PHASES.md](./PHASES.md).

> **⚠️ Phase-файлы Wave 1 — placeholder под прежнюю архитектуру.** Каждая phase будет регенерирована в начале Wave 1 на основе актуальных ADR + результатов Wave 0 retro.

## Risks specific

- **R-04** (runaway costs): cost-caps per task/agent/cell обязательны; Master-Agent layer добавляет ~+15–20% per vertical task — monitor budget guards
- **R-05** (data leak — critical, Business API): bot читает private DM-ы → consent UX обязан быть chrome-cleared + audit на 100%; единичная утечка = существенный репутационный hit
- **R-08** (регуляторика): 152-ФЗ disclosure + РКН-уведомление update — обязательно до production-trial
- **R-11** (retention): TTFV ≤5 мин — критично для friends
- **R-12** (scope): соблазн добавить Pixel Department — strictly NO, это Wave 2
- **R-29** Open: vertical-template content — in-house domain-expertise обеспечивает качество (founder + команда); deep Master-prompts — first-draft в Wave 1, hardening в Wave 2 retro

## Артефакты к концу волны

- Working pre-alpha на staging
- 3 templates (horizontal + 2 vertical) с полным workflow
- Master-Agent layer базовый класс + 2 vertical-Master-инстанции + deep Master-prompts в `contracts/role-prompts/masters/`
- Coordinator API retrofit под subordinate-mode validated через integration tests
- Horizontal role-prompts hardened pass (Phase 01.1 retro deliverable)
- 3 MCP-сервера (наши): telegram-mcp v0.2 (Business API), yandex-disk, imap-smtp
- Telegram Business API consent UX + audit log + 152-ФЗ disclosure
- Onboarding wizard + 3 demo-сценария + horizontal-vs-vertical routing
- ЮKassa подключена, тестовые платежи прошли
- Audit log заполняется (включая 100% Business API DM-чтений + bot-sends с consent_id)
- 10+ friends-клиентов активны; ≥3 подключили Telegram Business API
- Feedback log с insights для Wave 2
