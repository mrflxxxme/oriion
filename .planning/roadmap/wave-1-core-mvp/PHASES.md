# Wave 1 — Phase Index

> ⚠️ Phase-файлы Wave 1 — placeholders. Структура волны и phase-list финализируются при старте Wave 1 на основе:
> - Текущего scope из [README.md](./README.md)
> - Wave 0 retro outcomes
> - Актуальных ADR из [decisions/](../../decisions/README.md)

## Высокоуровневые phase-направления Wave 1 (revision 2026-05-15)

| Phase | Направление | Owner | Релевантные ADR |
|---|---|---|---|
| 01.1 | **Master-Agent layer + 2 vertical-templates** (Marketing-agency + Telegram-крейтор) + **Coordinator retrofit** under subordinate-mode + **horizontal role-prompts hardening pass** + **Coordinator generalization: произвольные промпты** (AC-W1-16/24/25 — удаление scripted-framing, артефакт-типы от Координатора) | Senior Backend + Tech Lead | [ADR-017](../../decisions/ADR-017-vertical-templates.md), [ADR-022](../../decisions/ADR-022-coordinator-wizard-llm-hybrid.md), [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md) |
| 01.2 | Memory: cell + role (двухуровневая, manual control) + persistent conversation history | Senior Backend | [ADR-011](../../decisions/ADR-011-memory-2-level.md) |
| 01.3 | Артефакты: Yjs документы + S3 ассеты + citeable URLs | Senior Backend + Frontend | [ADR-012](../../decisions/ADR-012-artifacts.md) |
| 01.4 | Биллинг: T-кредиты + ЮKassa + Trial 14 дней + Solo тариф + BYOK режим | Senior Backend | [ADR-008](../../decisions/ADR-008-credits-billing.md) |
| 01.5 | Dashboard UI (Vite + React + TanStack Router, без Pixel) | Senior Frontend | [ADR-001](../../decisions/ADR-001-modular-monolith.md) |
| 01.6 | Security guardrails: input/output фильтр + capability sandboxing + DLP-сканер | Tech Lead | [ADR-014](../../decisions/ADR-014-security.md) |
| 01.7 | RBAC: Owner + Member (Admin + Viewer — Wave 2) | Senior Backend | [ADR-014](../../decisions/ADR-014-security.md) |
| 01.8 | Auth extensions: 2FA TOTP, magic-link, Yandex ID + VK ID OAuth | Tech Lead | [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) |
| 01.9 | Onboarding wizard (3 шага) + auto-spawn trial-cell + horizontal-vs-vertical routing + per-template demo-сценарии | Frontend + Founder | [ADR-022](../../decisions/ADR-022-coordinator-wizard-llm-hybrid.md), [ADR-016](../../decisions/ADR-016-team-first-ux.md) |
| 01.10 | Первые MCP-серверы (наши): **telegram-mcp v0.2 (Read + post + Business API)**, yandex-disk-mcp, imap-smtp-mcp + Business API consent UX + 152-ФЗ disclosure + РКН-уведомление update | Middle Backend | [ADR-013](../../decisions/ADR-013-mcp-protocol.md), [ADR-030](../../decisions/ADR-030-telegram-business-api.md) |

## Acceptance gate to Wave 2

См. [README.md](./README.md) — секция «Метрика успеха».

Конкретные phase-spec'ы (tasks + acceptance criteria + dependencies graph) генерируются при старте Wave 1.
