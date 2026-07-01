# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-01 (**Workflow automation — ADR-037 autonomy redesign + Block A safety rails**)
- Session: `hungry-nash-01feac`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. 01.1-retro ✅ · 01.2 Master-Agent core ✅ · 01.3 Billing core ✅ · 01.4 Memory ✅ · 01.4b Memory auto-extraction ✅ (**merged — PR #73**).
- **This session is NOT a product phase.** It is a **workflow-infra** change: a `/grill-me` session that crystallized how the project moves from "one Claude session per phase + founder reviews/merges every PR" to an **autonomous multi-phase runner where the strengthened gate-stack is the merge authority** ([ADR-037](./decisions/ADR-037-autonomous-multiphase-runner.md), 8 decisions D1–D8), plus **Block A (safety rails) built + tested**.
- **What this PR delivers (Block A rails — ADR-037 D2/D3):** `.claude/autonomy/` (`tripwire.yaml` path-globs · `evidence-schema.json` · `README.md`) + `scripts/autonomy/verify_evidence.py` (evidence freshness+PASS verifier, stdlib, ASCII-safe, **7/7 scenario-tested**) + `scripts/autonomy/classify_tripwire.py` (diff→tripwire classifier, exit 10=ack) + `.github/workflows/ci-evidence.yml` (**non-breaking** evidence gate) + ADR-037 + cross-refs (ADR-015/023/027 + decisions/README). Both scripts ruff-clean.
- **Branch:** `claude/hungry-nash-01feac` (off `origin/main`). Focused PR → `main`. **Rails must land BEFORE the runner** (Blocks B–E) — founder's consent to full-autonomy merge (D1) is conditioned on D2/D3 existing.
- ⚠️ **Dual-tree guard:** canon `.planning/` is in the **worktree**; the outer `…/TEAMLY_RU/.planning` is stale. Anchor to `git rev-parse --show-toplevel`.

## Active blockers (none block this infra PR)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## Founder actions for this PR

1. **Merge** the focused Block-A PR (`claude/hungry-nash-01feac` → `main`).
2. **Branch protection (one-time, repo-admin):** add `ci-evidence` to the required status checks on `main` (alongside `ci-backend`/`ci-security`/`ci-frontend`) — else the evidence gate runs but doesn't block the merge button. Via GitHub settings or `gh api`.
3. **Later (Block C):** one-time Telegram channel setup (saved `chat_id`) for phone-side `/ack` (`/telegram:configure`).

## Next actions (build continuation — ADR-037 Blocks B–E)

- **Block B — Front autonomy (D4/D5):** auto-discuss/escalation policy (`.claude/autonomy/escalation-policy.md`) + decisions-log + judge-panel wiring on wide forks via the `evaluator` role.
- **Block C — Runner (D6/D8):** `/autonomy:run` slash-command (discuss→plan→execute→gates→auto-merge/tripwire-pause→next) + auto-merge-on-green + `RUN-QUEUE.md` + `PushNotification` + Telegram bridge + the scoped pre-merge tripwire hook (settings.json).
- **Block D — Self-healing (D7):** auto-revert on post-merge regression + autonomous fix-loop + regression-watch.
- **Block E — Parallelism (D6):** opt-in worktree for genuinely-independent phase tracks.
- **Known gap to close in B/C:** the 11 role dirs (`.claude/agents/<role>/`) are handbooks, NOT native spawnable subagents — the runner needs a role-prompt loader or native-subagent conversion to actually delegate.

## Next product phase

**Phase 01.5 — Артефакты** ([ADR-012](./decisions/ADR-012-artifacts.md)): Yjs-документы + S3-ассеты + citeable `artifact://` URLs. Unchanged by this infra session. (When the autonomous runner is live, 01.5 becomes the first phase run through it end-to-end.)
