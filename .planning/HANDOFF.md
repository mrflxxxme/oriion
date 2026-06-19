# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-19 (**Wave-1 kickoff — Phase 01.2 Master-Agent core, AC-W1-3**)
- Session: `pedantic-satoshi-8ced82`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. **Phase 01.1-retro = ✅ COMPLETE** (#58–66 merged). **Phase 01.2 (Master-Agent core) = ✅ code-complete + locally verified (this PR).**
- **What this PR delivers:** the two-tier Master-Agent layer (ADR-029, AC-W1-3) — the foundation all Wave-1 verticals sit on — proven end-to-end with the **Marketing-agency РФ** reference vertical. ADR-029 flipped **Proposed → Accepted**. Wave-1 `PHASES.md` regenerated (dependency-first 01.2→01.12).
- **Branch:** `claude/pedantic-satoshi-8ced82` (off `origin/main` = `1a90ba9`). Focused PR → `main` → founder-merge.
- ⚠️ **Dual-tree guard (it bit twice this session):** canon `.planning/` is in the **worktree**; the outer `…/TEAMLY_RU/.planning` is stale. Anchor to `git rev-parse --show-toplevel`. (The ADR Explore agent read the stale tree → falsely reported ADR-033/036 "missing"; they exist in canon. A Master-prompt Write first landed in the stale tree → relocated.)

## Active blockers (unchanged; none block 01.2)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Phase 01.3) |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН update | Founder + юрист | gates **Phase 01.11** (Business-API), NOT 01.2/01.9 |

## What just happened — Phase 01.2 (2026-06-19)

Founder-process: bootstrap-from-worktree + dual-tree guard → `/grill-me` (8 forks) → Plan-agent code-grounded design → execute (9 logical commits) → local CI + multiagent audit + gsd-verifier → exit ritual → focused PR.

**Implemented (ADR-029, AC-W1-3):**
- `StrategicContext` (`agents/strategic_context.py`) + optional `CoordinatorDeps.{strategic_context, master_recorder}` (additive, default `None` → horizontal path byte-identical).
- `PlanExecutingCoordinator.run` threads the strategic brief into the inner deps + prepends a domain preamble only when present (also fixes the previously-dropped depth fields).
- `agents/master.py` — `MasterPlan` / `MasterResponse` / `MasterDeps` / `MasterCallBilling` + `build_master_{plan,synthesis}_agent` (split model: plan=deepseek-chat, synthesis=R1).
- `runtime/dispatch.py` — `MasterAgent` orchestration object (CEO over the `PlanExecutingCoordinator` COO, reusing the same leaf runner) + `record_master_call_step` (`step_type='llm_call'`) + `resolve_master` (vertical detection via `Cell.vertical_template_slug`) + vertical-scoped `_resolve_archetype_id`.
- `runtime/orchestrator.py` — optional `master_step_recorder` → ctx-aware `master_recorder` so the Master's plan+synthesis calls fold into the SAME `ctx.accumulated_cost`; the 50-credit per-task cap covers the **Master + children aggregate** (R-32/R-04). **2 physical task levels** (Coordinator runs inside the Master's single run as `task_steps`).
- `router_service.py` — `master`/`master_synthesis` model + max-token entries.
- `role_prompt_loader.py` — `load_master_prompt(masters/<vertical>.md)`; `scripts/sync_role_prompts.sh` now mirrors the `masters/` subdir recursively (CI `diff -rq` passes).
- Marketing-agency seed (`agency_marketing_ru_v1.py` — Master archetype reusing the horizontal specialists) + provisioning wiring.
- `contracts/role-prompts/masters/agency_marketing_ru.md` (AI baseline, `status: draft`) + `verticals/agency-marketing-ru/golden-dataset/` scaffold (methodology + 2 example tasks + 5 adversarial probes).
- Cost authority reconciled (grill #7): `task.total_cost_credits` step-sum is the single source of truth; the Master path does NOT call `rollup_task_cost` (would double-count steps + lineage children — documented).

## Verification state

- **CI-equivalent, all green (local, post-audit-remediation):** `ruff check src tests` + `ruff format --check src tests` ✓ · `mypy --strict src` **163 files** ✓ · unit `pytest -m "not integration and not live"` **739 passed, 1 skipped** (cov **90.45%**) · per-module gates **agents 98% / runtime 87% / tasks 99% / billing 100%** (≥85) · integration `pytest -m "integration and not live"` **29 passed** (real testcontainers PG; +1 new Master-billing test) · `bandit -r src` **0 issues** · role-prompts drift `diff -rq` **DRIFT-OK** · tools-allowlist **OK**.
- **Adversarial audit (Workflow, 17 agents, 5 lenses + goal-backward):** 0 P0 / 0 P1 / 5 P2 / 3 P3 — all addressed in `c157f50` (token rollup, Master pre-call budget gate, budget-metric label, dropped stale-zero field, AC-3.2 test + AC-3.6 wording). No correctness/security/regression defects.
- **8 AC-W1-3.x green** — see [`phases/01.2-master-agent-core.md`](./roadmap/wave-1-core-mvp/phases/01.2-master-agent-core.md).
- **Live-валидация — НЕ выполнена** (founder-action, нужен funded DeepSeek + dev stack) — see Next actions.
- The PR's GitHub Actions (ci-backend / ci-frontend / ci-security) is the binding gate at founder-merge.

## Next actions (founder)

1. **Merge** the focused PR (`claude/pedantic-satoshi-8ced82` → `main`).
2. **Live golden** on funded DeepSeek (worker tract touched — green units insufficient, per memory `live-golden-async-dispatch-findings`): provision a Marketing-agency cell, `POST /tasks/{id}/run`, assert dispatch <1s, `task.completed` carries a real `MasterResponse.final_artifact_markdown`, `0 < total_cost_credits ≤ 50`, `/metrics` shows the +2 Master LLM calls.
3. **Evaluator run** (ADR-026) → promote the Master prompt + archetype `draft → reviewed` (≥75% golden + 100% adversarial); materialize the remaining golden tasks toward 30 (founder domain-expertise step).
4. Fast-follow (optional): add `'master'` to the `agent_archetypes.role_category` CHECK (currently reuses `'coordinator'`).

## Next phase

**Phase 01.3 — Billing** (ADR-008): T-credit ledger + Trial-14d/500 + Solo tier + per-task/cell caps + BYOK plumbing + ЮKassa **test mode** (live-flip gated on OQ-02/OQ-19).
