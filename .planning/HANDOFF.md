# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-18 (**Phase 01.1-retro closeout — post-merge audit + fix-to-green**)
- Session: `interesting-knuth-f649a6`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. **Phase 01.1-retro (AC-W1 hardening pin block) = ✅ VERIFIED-COMPLETE (scoped).**
- **Lineage:** `origin/main` = `9aa776f` (this worktree's HEAD). The four AC-W1 domain PRs are merged on top of `6b40084` (= PR #53 merge): [#58](https://github.com/mrflxxxme/oriion/pull/58)/[#59](https://github.com/mrflxxxme/oriion/pull/59)/[#60](https://github.com/mrflxxxme/oriion/pull/60)/[#61](https://github.com/mrflxxxme/oriion/pull/61). **PR #53 itself is MERGED** (the prior HANDOFF's "open, awaiting founder-merge" is stale).
- ⚠️ **Local `main` ref is stale** (`0a9eee8`, Phase-00.2 era) — canon base is **`origin/main`**, NOT local `main`. Don't diff/PR against local `main`.
- This session's fix lives on branch **`claude/interesting-knuth-f649a6`** (uncommitted at time of writing → see Next actions; opens ONE PR → main).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Wave 1) |

## What just happened — 01.1-retro closeout (2026-06-18)

Founder-process: `/grill-me` (6 развилок → DoD=scoped-complete; audit=Workflow-harness; one-PR→founder-merge; verify=gsd-verifier+local-CI; **AC-4/5 = fix-to-green**) → multiagent adversarial audit → fix-to-green → exit ritual.

1. **Step-3 verify-before-flip (код, не доку):** the claimed "AC-W1-2/13/14/15 closed in #48/49/50+ADR-035" contradiction is a **phantom** (no canon doc claims it). Verified all four are genuinely residual (2 = table scaffolding only; 13 = metrics+pricing wired but cost still estimated; 14 = bucket only; 15 = stub) → correctly DEFERRED.
2. **Adversarial audit** of the merged combined diff `6b40084..HEAD` (48 files; Workflow harness — 32 agents, 3 lenses + 4 focused-AC, each finding adversarially re-verified) → **0 P0 / 4 P1 / 6 P2 / 6 P3**. Key: **2 of the 8 "closed" pins did not meet acceptance** — AC-W1-4 relay was dead code (never scheduled/imported), AC-W1-5 testcontainers test never delivered (still an in-memory stub).
3. **Fix-to-green** (branch `claude/interesting-knuth-f649a6`):
   - `fix(runtime): AC-W1-4` — self-rescheduling outbox relay ([ADR-036](./decisions/ADR-036-outbox-relay-self-scheduling.md)) wired into `worker.py` + per-row poison isolation + deterministic order. Closes the dead-relay (P1) + poison-message (P1).
   - `test(tasks): AC-W1-5` — `backend/tests/tasks/test_cancel_cascade_integration.py` (real-PG testcontainers cancel-cascade + real-dispatch SSE order).
   - `fix(_shared): AC-W1-9` — `refresh_app_secrets` drops DB/Redis lru_caches so a rotated `DATABASE_URL`/`REDIS_URL` actually applies in-process (P1 SIGHUP partial-apply).
   - `docs/ci` — `deploy-staging.yml` stale "AC-W1-9 PARTIAL" comment → CLOSED; rotation runbook clarity.
   - Doc-sync: `01.1-retro.md` (2026-06-18 closeout note + Status flip), `STATUS.md`, `JOURNAL.md`, ADR-036 + decisions index.

## Verification state

- **CI-equivalent, all green (local, isolated):** `ruff` + `ruff format --check` ✓ · `mypy --strict` **158 files** ✓ · unit `pytest -m "not integration and not live"` **682 passed, 1 skipped** (SIGHUP Unix-only) · integration `pytest -m "integration and not live"` **25 passed** (real testcontainers `pgvector/pgvector:pg16`; 23 prior + 2 new AC-W1-5).
- **Tier-4 review (ADR-027):** ADR-036-link present; code + security reviewer-agents run on the diff this session.
- **Live-валидация — НЕ выполнена** (founder-action, нужен полный стек + funded keys): live golden AC8/9/10 + AC-W1-9 staging cutover.
- The PR's GitHub Actions (ci-backend / ci-frontend / ci-security) is the binding CI gate at founder-merge.

## Next actions (founder)

1. **Open + merge the closeout PR** `claude/interesting-knuth-f649a6` → `main` (per ADR-027 — Tier-4 = explicit founder approve; touches delivery-semantics + secret-rotation + ADR-036).
2. **Live golden AC8/9/10** on funded keys (DeepSeek/Yandex/GigaChat) — the carried-over live-validation.
3. **AC-W1-9 staging cutover** (chip `task_8d5ce94c`): no secret on VM disk + Lockbox version-bump pickup without redeploy.
4. **Pin real `RU_TRUSTED_CA_SHA256`** — `backend/Dockerfile:41` is still `REPLACE_WITH_REAL_SHA256_BEFORE_MERGE` (chip #54 placeholder); needed before the prod image build.
5. **obs/IaC follow-up** (the verified-residual pins): AC-W1-2 (per-step TaskStep persistence) · AC-W1-13 (cost from `record_llm_cost` + worker-process metric exposition) · AC-W1-14 (Loki retention=90d + archival job) · AC-W1-15 (real Telegram/PagerDuty receivers).
6. **P2/P3 backlog** (10 findings, in PR body + the follow-up chip): cancel_task terminal-status guard · read_url DNS-rebinding SSRF (now LLM-reachable) · web_search body-size cap · `tasks.outbox` RLS/`oriion_app` grant · BFS `descendant_ids` cycle guard · Yandex `.//error` XPath anchor · `recover=True` truncated-XML.
7. After merge → **functional Phase 01.1** (Master-Agent layer + vertical-templates); AC-W1-3 (Master-Agent schema) unblocks once ADR-029 moves Proposed→Accepted (Wave-2).

## Exit ritual (this session)

- [x] Bootstrap-4 + dual-tree guard (anchored to `git rev-parse --show-toplevel`; local-`main`-stale noted)
- [x] `/grill-me` — 6 развилок resolved (AskUserQuestion)
- [x] Multiagent adversarial audit (Workflow, 32 agents) → 0 P0 / 4 P1 / 6 P2 / 6 P3, adversarial-verified
- [x] Step-3 verify-before-flip (AC-W1-2/13/14/15 truth established in code; phantom contradiction documented)
- [x] Fix-to-green: AC-W1-4 relay (ADR-036) + AC-W1-5 integration test + AC-W1-9 SIGHUP P1 + doc-nits
- [x] CI-equiv green (ruff/format/mypy-158/unit-682/integration-25)
- [x] Tier-4 reviewer-agents (code + security) on the diff
- [x] Doc-sync: 01.1-retro.md closeout + STATUS.md + JOURNAL.md + ADR-036 + decisions index + HANDOFF.md (this file)
- [ ] **Commit + open PR** (this session, final step) → founder merge (per ADR-027)
- [ ] **Founder:** live golden + staging cutover + CA-sha256 pin + obs/IaC follow-up + P2/P3 chip
