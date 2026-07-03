# Wave 1 — Phase Index

> Регенерировано 2026-06-19 (session `pedantic-satoshi-8ced82`) при старте функциональной части Wave 1.
> Порядок — **dependency-first, security-before-PII** (grill-решение). Заменяет прежние
> placeholder-направления (revision 2026-05-15) на конкретную фазовую последовательность под
> актуальные ADR + Wave-0/01.1-retro outcomes. 01.1-retro (AC-W1 hardening) — ✅ закрыта (PR #58–66).

## Фазовая последовательность (функциональный Wave 1)

| Phase | Направление | Status | Релевантные ADR | Gating |
|---|---|---|---|---|
| 01.1-retro | AC-W1 hardening pin block (async-dispatch, obs/IaC, billing-scaffold) | ✅ Complete | ADR-032/034/035/036 | — |
| **01.2** | **Master-Agent core (ADR-029, AC-W1-3)** — `MasterAgent` base + Coordinator subordinate-mode retrofit (`StrategicContext` in/out) + `parent_task_id` chain + Marketing-agency РФ reference vertical end-to-end + evaluator-gate scaffold | ✅ **Code-complete (this PR)** | [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md), [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md), [ADR-022](../../decisions/ADR-022-coordinator-wizard-llm-hybrid.md) | — |
| **01.3** | Биллинг core — T-кредиты ledger + Trial 14д/500 + Solo тариф + per-cell/per-day caps + BYOK plumbing + credit-rate API. **ЮKassa → focused follow-up 01.3b** (grill 2026-06-22) | ✅ **Code-complete** | [ADR-008](../../decisions/ADR-008-credits-billing.md), [01.3 spec](./phases/01.3-billing.md) | 01.3b live-flip → OQ-02/OQ-19 |
| 01.3b | Биллинг ЮKassa test-mode top-up (payment-create + webhook→credit + idempotency) | ⏳ Pending | [ADR-008](../../decisions/ADR-008-credits-billing.md) | **GATED: OQ-02 + OQ-19** |
| 01.4 | Memory — cell + role (двухуровневая, manual control) + conversation history (FIFO + summary seam) + «запомни». **256-dim Yandex + single-schema RLS** (grill 2026-06-23). | ✅ **COMPLETE** (auto filter-agent + summarizer → 01.4b ✅) | [ADR-011](../../decisions/ADR-011-memory-2-level.md), [01.4 spec](./phases/01.4-memory.md) | — |
| 01.4b | Memory auto-extraction — LLM filter-agent (auto-after-task) + LLM conversation summarizer + orchestrator post-task wiring + `memory_curator` archetype seed + live golden | ✅ **Code-complete** (2026-06-24, `tender-clarke-a1cd06`) | [ADR-011](../../decisions/ADR-011-memory-2-level.md), [01.4b spec](./phases/01.4b-memory-auto-extraction.md) | — |
| 01.4-ui | Memory UI — «Что помнит [агент]» view/edit/delete panel (grill Q6) | ⏳ Pending | [ADR-011](../../decisions/ADR-011-memory-2-level.md) | — |
| 01.5 | Артефакты — Yjs документы + S3 ассеты + citeable `artifact://` URLs | ✅ **Complete** (2026-07-03, `/autonomy:run` pilot, PR #78) | [ADR-012](../../decisions/ADR-012-artifacts.md), [ADR-038](../../decisions/ADR-038-artifacts-envelope-schema.md), [01.5 spec](./phases/01.5-artifacts.md) | — |
| 01.6 | Security guardrails — input/output фильтр + capability sandboxing + DLP-сканер | ✅ **Code-complete** (2026-07-03, `/autonomy:run`; детерминированный слой B, security-context, 0 миграций/tripwire → auto-merge) | [ADR-014](../../decisions/ADR-014-security.md), [ADR-039](../../decisions/ADR-039-security-guardrails-context.md), [01.6 spec](./phases/01.6-security-guardrails.md) | **до любого PII-surface** |
| 01.7 | RBAC — Owner + Member (Admin/Viewer → Wave 2) | ⏳ Pending | [ADR-014](../../decisions/ADR-014-security.md) | — |
| 01.8-mail | **Реальный `YandexSmtpEmailSender`** — impl `EmailSender`-порта (сейчас prod=NoOp) + mock-транспорт тесты; live-send валидируется когда SMTP-креды в канон. `.env`. **Pre-alpha prerequisite** (верификация email обязательна до 1-й задачи per ADR-007). Grill 2026-07-03 (Option A) | ⏳ Pending | [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) | **блокер pre-alpha** |
| 01.8 | Auth extensions **core** — 2FA TOTP (pyotp) + magic-link (на `EmailSender`-порту) + session-list backend. Автономно (моки; без внешних кредов). Grill split 2026-07-03 | ⏳ Pending | [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) | — |
| 01.8b | Auth OAuth — Yandex ID + VK ID flow + account-linking. **Нужны OAuth client creds** (регистрация приложений founder'ом) → live follow-up | ⏳ Pending | [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) | client creds |
| 01.9 | MCP-серверы (наши) — telegram-mcp v0.2 **Bot-API** scope + yandex-disk-mcp + imap-smtp-mcp | ⏳ Pending | [ADR-013](../../decisions/ADR-013-mcp-protocol.md) | — |
| 01.10 | Telegram-крейтор 2-й vertical (Master + prompts + Bot-API content-демо) + horizontal prompt-hardening. **Process (grill 2026-07-03):** research-first фаза (domain-brief: ЦА + поведенческий паттерн + ключевые аспекты, cited) → autonomous draft-промпты grounded в brief → golden+evaluator → founder review-gate `draft→reviewed` (brief едет в PR). Amend ADR-026 | ⏳ Pending | [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md), [ADR-017](../../decisions/ADR-017-vertical-templates.md), [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md) | TG bot-token + test-канал (live-демо) |
| 01.11 | Telegram **Business-API** surface — consent UX + DM read/send + 152-ФЗ disclosure + РКН + 100% audit | ⏳ Pending | [ADR-030](../../decisions/ADR-030-telegram-business-api.md) | **GATED: OQ-32 + OQ-33** (feature-flagged) |
| 01.12 | Dashboard UI + Onboarding wizard (3 шага) + trial-cell auto-spawn + horizontal-vs-vertical routing + demo-сценарии | ⏳ Pending | [ADR-001](../../decisions/ADR-001-modular-monolith.md), [ADR-022](../../decisions/ADR-022-coordinator-wizard-llm-hybrid.md), [ADR-016](../../decisions/ADR-016-team-first-ux.md) | integration last |

Каждая фаза получает свой `phases/01.X-<slug>.md` spec на своём старте (не сейчас).

## Grill-решения старта Wave 1 (session `pedantic-satoshi-8ced82`, 2026-06-19)

1. **Первая фаза** = Master-Agent **core**, отделена от верти­калей (focused split).
2. **Reference vertical** = Marketing-agency РФ (вне Telegram-legal-критпути OQ-32/33).
3. **Coordinator-контракт** = опциональный типизированный `StrategicContext` IN (горизонталь не тронута); Coordinator возвращает существующий `CoordinatorOutput`, Master синтезирует `MasterResponse`.
4. **Telegram** (01.9/01.11) — split: Bot-API + scaffold сейчас; Business-API за feature-flag, gated на OQ-32/33.
5. **Биллинг** (01.3) — phased: вся логика против ЮKassa **test mode**; live-flip = credential swap, gated на OQ-02/OQ-19.
6. **Prompt-bar** Master = ADR-026 'reviewed' (founder-edit + golden ≥75% + adversarial 100%); friend-loop 'locked' → Wave-2 retro.

## Acceptance gate to Wave 2

См. [README.md](./README.md) — секция «Метрика успеха».
