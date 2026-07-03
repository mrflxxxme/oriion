# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-03 (**Phase 01.5 Артефакты — первый прогон `/autonomy:run`, code-complete**)
- Session: `charming-kepler-c814fe` (autonomous runner, ADR-037 pilot)
- Agent: @claude-fable

## Project status

- **Wave:** Wave 1 (Core MVP) — in progress. 01.1-retro ✅ · 01.2 ✅ · 01.3 ✅ · 01.4 ✅ · 01.4b ✅ · **01.5 = this PR (autonomy-pilot)**.
- **01.5 «Артефакты» (ADR-012 / [ADR-038](./decisions/ADR-038-artifacts-envelope-schema.md)):** новый bounded context `backend/src/artifacts/` — envelope-схема 7 таблиц (`artifacts_0001`, FORCE RLS, immutable versions), Yjs bytea+pycrdt синхронный merge (REST-only Wave 1), S3 presigned flow против MinIO/YOS, `artifact://` resolver, `cell_storage_usage` учёт, контракты переписаны. `tasks.task_artifacts` НЕ тронут — его висячие `s3_key`/`yjs_document_id` теперь резолвятся против artifacts-таблиц.
- **Автономный цикл отработал:** 9 forks (6 owned / 2 escalated non-blocking / 1 judge-panel → ADR-038) · 3-lens adversarial audit поймал 1 P1 (concurrent double-complete) — закрыт с тестом гонки · ci-evidence freshness circularity починен (`verify_evidence.py` walk мимо evidence-only коммитов).
- **Gates финального кода:** ruff clean · mypy --strict 214 · bandit 0 · unit 852 · integration 55 (real PG + MinIO) · `src/artifacts` 93%.
- ⚠️ **Dual-tree guard:** canon `.planning/` в активном worktree; anchor `git rev-parse --show-toplevel`.
- ⚠️ Pre-merge tripwire hook armed: merge этого PR требует approved `/autonomy:ack` (diff трогает `backend/migrations/versions/**` + `.planning/contracts/**`).

## Pending founder actions

1. **Tripwire ack на PR 01.5** — RUN-QUEUE `ack-needed` запись (создаётся при открытии PR): db_migrations (чистый greenfield CREATE новой схемы + RLS, runner_nuance = низкий риск) + public_api_contracts (SKELETON → implemented, единственный источник правды). `/autonomy:ack <ID> approved` → раннер мержит.
2. **Эскалации (non-blocking, leans уже исполняются):** RQ-20260701-001 co-editing scope (lean B: y-websocket отложен до co-editing UI) · RQ-20260701-002 storage-квоты (lean B: track-only, enforcement = billing follow-up).
3. **Chip `task_6cdb162a`** — hardening-хвосты аудита (janitor wiring, body-caps, presign-overwrite window, live-Yjs bytes accounting) — запустить после merge.

## Active blockers (none block this PR)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## Next product phase

**Phase 01.6 — Security guardrails** ([ADR-014](./decisions/ADR-014-security.md)): input/output фильтр + capability sandboxing + DLP-сканер. Помечена «до любого PII-surface». Следующий кандидат для `/autonomy:run 01.6`.
