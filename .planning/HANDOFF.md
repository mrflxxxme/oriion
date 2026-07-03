# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-03 (**Phase 01.6 Security guardrails — `/autonomy:run`, code-complete**)
- Session: autonomous runner (ADR-037), branch `claude/autonomy-run-01-6-mpbq2u`
- Agent: @claude

## Project status

- **Wave:** Wave 1 (Core MVP) — in progress. 01.1-retro ✅ · 01.2 ✅ · 01.3 ✅ · 01.4 ✅ · 01.4b ✅ · 01.5 ✅ (merged `a326f7a`) · **01.6 = this PR**.
- **01.6 «Security guardrails» ([ADR-039](./decisions/ADR-039-security-guardrails-context.md), реализует [ADR-014](./decisions/ADR-014-security.md) §2/§3):** новый bounded context `backend/src/security/` — детерминированный слой B (regex + checksum), детекторы-порты с апгрейд-швом B→A (ML). RU-ПДн DLP (ИНН-10/12 + СНИЛС checksum, паспорт/телефон/email) + prompt-injection эвристики + capability-классификатор. **Ноль таблиц/миграций** (DLP пишет существующий `audit.audit_log`), **ноль tripwire** → **auto-merge на зелёном** (classify_tripwire exit 0).
- **Runtime-швы** (зеркало `memory_extraction`/`quota_admission`, default None ⇒ no-op): output-DLP A3 hard-block на orchestrator success-пути (screen `_dlp_screen_text` = полный deliverable) + injection B1-sanitize на `web_search_runner`. **Оба флага (`security_dlp_enabled`, `security_injection_scan_enabled`) default OFF в Wave-1** — substrate готов, enforcement активируется в 01.9 (нет исходящего PII/коннектор-surface до 01.9).
- **Adversarial audit (3 линзы, refute-by-default):** SECURE ✅ PASS (0 P0/P1, инвариант «сырое ПДн не утекает» устоял) · SOUND → 1 P1 (усечённый DLP-скрин → полный `_dlp_screen_text`) закрыт · NO-REGRESSIONS → 1 P2 (injection default-ON калечил веб-контент → default OFF + trim) закрыт · P3 robustness (except Exception) закрыт.
- **Gates финального кода:** ruff clean · mypy --strict 224 · bandit 0 · unit 950 · `src/security` 97% / `src/runtime` 87%. Docker/live не требуются (детерминированная фаза).

## Pending founder actions

**НЕТ блокирующих** — фаза tripwire-free, auto-merge на зелёном CI (никакого `/autonomy:ack` не нужно). Раннер сам мёржит после зелёных чеков + post-merge health-check.

Deferred (НЕ блокирует merge; трекается для 01.9 при активации enforcement):
1. **ИНН-10 precision-tuning** — checksum пропускает ~10% произвольных 10-значных чисел (юрлицо-ИНН, high-FP). Перед `security_dlp_enabled=True` в 01.9: контекстный якорь «ИНН» ИЛИ low-confidence ИЛИ исключить ИНН-10 как не-ПДн. Детали — [01.6 spec §Enforcement activation](./roadmap/wave-1-core-mvp/phases/01.6-security-guardrails.md).
2. **Активация обоих guardrail-флагов в 01.9** вместе с owner-config surface + реальным capability-gate (`requires_approval` в dispatch outward-tools).

## Active blockers (none block this PR)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## Next product phase

**Phase 01.7 — RBAC** ([ADR-014](./decisions/ADR-014-security.md)): Owner + Member (Admin/Viewer → Wave 2). Грил 2026-07-03 pre-resolved: **flat member visibility** (все члены cell видят все артефакты; Owner vs Member = права, не видимость) + **visibility stub-колонка** (`visibility text DEFAULT 'cell-shared'` в artifacts-миграции 01.7, fast-default, без backfill, не enforced — задел под per-artifact privacy B в Wave-2). Кандидат для `/autonomy:run 01.7`. Примечание: 01.7 добавит миграцию (existing artifacts table ALTER) → **db_migrations tripwire → ack-needed** (не greenfield).
