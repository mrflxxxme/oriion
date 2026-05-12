# Wave 1 — Core MVP (6 недель)

## Цель волны

**Pre-alpha релиз для 10-15 friends-клиентов.** Ядро продукта (без Pixel Department) функционально: 3 vertical-templates выполняют полезные задачи, биллинг считает, безопасность блокирует базовые векторы.

## Метрика успеха

- 10-15 friends-клиентов поставили ≥3 задачи каждый
- Task success rate ≥75%
- 3 vertical-templates работают: WB-Селлер + Маркетинг-агентство РФ + Telegram-крейтор
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
- Расширение каталога: 3 vertical-templates (WB-Селлер из W0 + Маркетинг-агентство РФ + Telegram-крейтор)
- Vertical-aware Coordinator prompts per template (ADR-022)
- Memory: cell + role (двухуровневая, manual control) — ADR-011 Wave 1 stage
- Persistent conversation history per agent (FIFO + summarization)
- Артефакты: документы Yjs + S3 для ассетов (ADR-012)
- Биллинг: T-кредиты + ЮKassa + Trial 14 дней + Solo тариф + BYOK режим (ADR-008)
- Dashboard UI (Vite + React + TanStack Router, без Pixel) — ADR-001
- Безопасность: input/output фильтр + capability sandboxing для dangerous tools (ADR-014)
- RBAC: Owner + Member (Admin + Viewer — Wave 2)
- LLM-gateway расширение: 2FA TOTP, magic-link, Yandex ID + VK ID OAuth
- Первые MCP-серверы (наши): telegram-mcp, yandex-disk-mcp, imap-smtp-mcp
- Onboarding wizard (3 шага) для landing — конвертит в trial-cell
- 1 demo-сценарий per vertical для wow-эффекта

**Nice (можно отложить в Wave 2):**
- Telegram-бот (только нотификации, не команды)
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

- **R-04** (runaway costs): cost-caps per task/agent/cell обязательны
- **R-11** (retention): TTFV ≤5 мин — критично для friends
- **R-12** (scope): соблазн добавить Pixel Department — strictly NO, это Wave 2
- **R-29** Open: vertical-template content — in-house domain-expertise обеспечивает качество (founder + команда)

## Артефакты к концу волны

- Working pre-alpha на staging
- 3 vertical-templates с полным workflow
- 3 MCP-сервера (наши): telegram, yandex-disk, imap-smtp
- Onboarding wizard + 3 demo-сценария
- ЮKassa подключена, тестовые платежи прошли
- Audit log заполняется
- 10+ friends-клиентов активны
- Feedback log с insights для Wave 2
