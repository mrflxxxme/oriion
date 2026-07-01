# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-01 (**Autonomy Block B — front autonomy D4/D5**)
- Session: `hungry-nash-01feac`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. 01.1-retro ✅ · 01.2 ✅ · 01.3 ✅ · 01.4 ✅ · 01.4b ✅ (#73). **Autonomy Block A ✅ (#74 merged).**
- **This session is NOT a product phase.** It continues the **autonomy workflow build** ([ADR-037](./decisions/ADR-037-autonomous-multiphase-runner.md), Blocks A–E; tracker `.claude/autonomy/BUILD-PLAN.md`).
- **Block A (merged, #74):** safety rails — tripwire config, evidence-schema + `verify_evidence.py` + `ci-evidence.yml`, `classify_tripwire.py`, ADR-037. **Branch protection on `main` applied** (require PR + `ci-evidence`/`ci-security`; linear history; enforce_admins off). Finding: `main` had zero protection before.
- **This PR delivers Block B (front autonomy — D4/D5):** `.claude/autonomy/escalation-policy.md` (D4 — own all impl+arch, escalate only product/market + tripwire) · `judge-panel.md` (D5 — wide-fork optimality via `evaluator` rubric + evidence emission) · `scripts/autonomy/log_decision.py` (decisions-log appender, tested) · `.claude/commands/autonomy/discuss.md` (**first slash-command** `/autonomy:discuss`) · `.claude/autonomy/BUILD-PLAN.md` (A–E tracker + the 3 protection toggles under Block C) · README update.
- **Branch:** `claude/autonomy-block-b` (off `origin/main` = `e4d9b38`). Focused PR → `main`.
- ⚠️ **Dual-tree guard:** canon `.planning/` is in the **worktree**; the outer `…/TEAMLY_RU/.planning` is stale. Anchor to `git rev-parse --show-toplevel`.

## Active blockers (none block this infra PR)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## Next actions (build continuation — ADR-037)

- **Merge** the Block-B PR (`claude/autonomy-block-b` → `main`, Squash/Rebase — linear history required).
- **Block C — Runner (next):** `/autonomy:run` (sequential chain + auto-merge-on-green + tripwire-pause) · `RUN-QUEUE.md` · `PushNotification` + Telegram bridge (one-time `chat_id`) · scoped pre-merge hook · **role-prompt loader** (close the gap: 11 role dirs are handbooks, not spawnable subagents) · **the 3 branch-protection toggles** (enforce `ci-backend`, `enforce_admins=true`, `delete_branch_on_merge=true`) — see `BUILD-PLAN.md`.
- **Block D — Self-healing:** auto-revert + fix-loop + regression-watch. **Block E — Parallelism:** opt-in worktrees + per-run budget cap.

## Next product phase

**Phase 01.5 — Артефакты** ([ADR-012](./decisions/ADR-012-artifacts.md)): Yjs + S3 + `artifact://` URLs. Unchanged by the autonomy build. When the runner (Block C) is live, 01.5 becomes the first phase run through it end-to-end (and a natural first real-world test of `/autonomy:discuss`).
