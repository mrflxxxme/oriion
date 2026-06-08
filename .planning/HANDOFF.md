# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-08 (Phase 00.6 PR-B **COMPLETE** + live-validation Exit ritual. PR #38 (C0–C12) + PR #39 (C13–C19) merged to main.)
- Session: `lucid-maxwell-c7e2a1` (Exit ritual after `gallant-lamport-f48eca` PR-B work)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — **closing**. All build phases complete + architecture **live-validated locally**. The only remaining Wave-0 item is the **founder staging 10× anchor run** (gate D5) — a Wave-0→Wave-1 gate, NOT a blocker for Phase 00.7.
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete ([PR #25](https://github.com/mrflxxxme/oriion/pull/25))
- **Architect-PR (pre-00.2)**: ✅ Complete ([PR #27](https://github.com/mrflxxxme/oriion/pull/27))
- **Phase 00.2 (Custom JWT auth)**: ✅ Complete (src.iam 86.69%)
- **Phase 00.3 (DB+RLS+multitenancy)**: ✅ Complete
- **Phase 00.4 (LLM gateway+MCP)**: ✅ Complete
- **Phase 00.2.5 (integration)**: ✅ Complete ([PR #32](https://github.com/mrflxxxme/oriion/pull/32))
- **Phase 00.5 / 00.5a (Pydantic-AI runtime)**: ✅ Complete
- **Phase 00.5b (runtime + tasks + orchestrator)**: ✅ Complete ([PR #35](https://github.com/mrflxxxme/oriion/pull/35); 5-agent audit; AC-W1-1..10)
- **Phase 00.6 PR-A (Stage A local infra)**: ✅ Complete ([PR #36](https://github.com/mrflxxxme/oriion/pull/36); 22 commits; AC-W1-11..15)
- **Phase 00.6 PR-B (Stage B + orchestrator-dispatch + live validation)**: ✅ **Complete** ([PR #38](https://github.com/mrflxxxme/oriion/pull/38) C0–C12 + [PR #39](https://github.com/mrflxxxme/oriion/pull/39) C13–C19; full 5-agent retro PASS; **architecture proven end-to-end on a live stack with real LLMs**)
- **Phase 00.7 (frontend skeleton)**: ⏳ **NEXT** — opens now (runs ∥ Wave-0 close per roadmap; API is proven + stable)
- **Phase 01.1 retro (Wave-1 hardening)**: ⏳ Pending — `roadmap/wave-1-core-mvp/phases/01.1-retro.md` holds AC-W1-1..23

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Wave 1) |

## What just happened — Phase 00.6 PR-B (C0–C19, 20 commits across PR #38 + #39)

**Closed the PR-A CRITICAL FINDING** (POST /tasks queued-but-never-dispatched) + shipped the full Stage-B surface + **live-validated the whole architecture**.

### Commit ledger

| # | Commit | |
|---|---|---|
| C0 | catch-up HANDOFF + STATUS | docs |
| C1 | **inline orchestrator-dispatch** `POST /tasks/{id}/run` + `runtime/dispatch.py` (ScriptedCoordinator pipeline) | feature |
| C2 | demo_market_brief AC8 cohort-semantic + exit codes | fix |
| C3 | **Terraform YC baseline** (VM+PG+Redis+Lockbox+DNS+Object Storage) | feature |
| C4 | `deploy-staging.yml` + deploy scripts | feature |
| C5 | Caddyfile real-ACME + staging-bootstrap runbook | feature |
| C6 | gate D5 amendment (α) + ADR-018 V4 drift | docs |
| C8 | `01.1-retro.md` (AC-W1-1..17) | docs |
| C9a | **full 5-agent retro audit** (4 HIGH fixed in-loop, verdict PASS) | audit |
| C10 | CVE-drift fix (aiohttp bump + trivy/pip-audit ignores) | fix |
| C11 | **live web_search (Brave)** wired into Researcher | feature |
| C12 | deploy-staging readiness gate | ci |
| **C13** | role-prompts packaged into image + UTF-8 console (live-validation finds) | fix |
| **C14** | **graceful intra-request provider failover** (`acomplete`) | feature |
| **C15** | leaf agents → `output_type=str` (close structured-output gap) | fix |
| **C16/17** | YandexGPT **5.1 Pro** (`yandexgpt/rc`) as the Yandex model | feature |
| **C18** | `max_tokens` 2048→8192 (writer was truncated) | fix |
| **C19** | AC9 content-plan parser matches wrapped/any-level headings | fix |

### Live validation (2026-06-08) — architecture PROVEN

Ran the real «Market & content brief» scenario against the live Docker stack with real keys. After fixing 7 deployment bugs (C13–C19, all invisible to unit tests), the full pipeline runs end-to-end:

`register → cell+team provisioning → POST /tasks → POST /run → researcher (live Brave web_search) + analyst + writer (real DeepSeek; YandexGPT 5.1 Pro failover) → 8 SSE events → 3 markdown artifacts → cost rollup`.

Result: **AC8 PASS** (~91s), **AC10 PASS** ($0.014/run), **AC9** matrix 5×4 ✅ + content-plan 10 ✅ + brief 1018 words (1500 target — the one tuning gap). Output quality is consultant-grade (TAM/SAM/SOM, real named RU competitors, 10-post plan). The brief-length gap is the AC8↔AC9 length-vs-latency trade-off → Wave-1 (streaming/Dramatiq AC-W1-16 + prompt tuning AC-W1-22/23).

### AC-W1 pin block (lift target: `01.1-retro.md`)

AC-W1-1..10 (00.5b), AC-W1-11..15 (00.6 PR-A), AC-W1-16..19 (00.6 PR-B), **+ live-validation pins:**
- **AC-W1-20** — single-source the packaged role-prompts (`backend/role_prompts/` ↔ `.planning/contracts/role-prompts/`).
- **AC-W1-21** — **Russian Trusted Root CA in the backend Docker image** (host has it; container doesn't → GigaChat TLS fails — breaks staging GigaChat too) + yandexgpt-pro/5.1 catalog enablement note.
- **AC-W1-22** — writer output conformance: brief ≥1500 words + content-plan format (prompt tuning).
- **AC-W1-23** — per-role `max_tokens` tuning + decouple AC8 latency from output length (streaming, ties AC-W1-16).

## Founder action queue (two independent tracks)

**Track A — close Wave-0 (staging anchor, when ready, costs YC money):**
1. `terraform apply` → DNS `staging.oriion.dev` → `gh secret/var set` (incl. `STAGING_DEPLOY_ENABLED=true`) → first deploy. Runbook: `docs/runbooks/staging-bootstrap.md`.
2. seed demo user → 10× demo run against staging → screen-record → evidence in `.planning/gates/evidence/wave-0-to-1/`.
3. AI flips `internal_demo_passed=true` + finalizes the Wave-0→Wave-1 gate.
> The architecture is already locally proven, so the staging run is for the audit-grade anchor evidence, not de-risking.

**Track B — start Phase 00.7 (frontend, in parallel):** see the kickoff message the founder was given. 00.7 builds the UI on the proven API; the founder can then click-test scenarios + tune brief length live.

## Keys / config state (local `backend/.env`, gitignored — NEVER in git)

- `DEEPSEEK_API_KEY` — funded, working (primary). `YANDEX_IAM_TOKEN` — refresh via `yc iam create-token` (TTL ~12h). `BRAVE_SEARCH_API_KEY` — real key set, `WEB_SEARCH_MOCK_MODE=false` (live search). `GIGACHAT_AUTH_KEY` + `BYOK_MASTER_KEY_B64` + `JWT_SECRET_ACCESS_V1` present.
- Staging equivalents live in Lockbox / `infra/terraform/terraform.tfvars` (gitignored) / VM `/opt/oriion/.env`.

## Carryover — read order for the next session

1. `README.md` → 2. **this HANDOFF.md** → 3. `STATUS.md` → 4. `agent-handbook/00-START-HERE.md` → 5. `roadmap/wave-0-foundation/phases/00.7-frontend-skeleton.md` (next phase) → 6. `_session-context/AUDIT-2026-05-26-PHASE-00-6-FINAL/AUDIT-REPORT.md`.

## Exit ritual (this session)

- [x] HANDOFF.md rewritten — Phase 00.6 PR-B complete + live validation + AC-W1-1..23
- [x] STATUS.md updated — Phase 00.6 ✅, Phase 00.7 next
- [x] phase-spec 00.6 status → Complete
- [x] JOURNAL.md appended — PR-B closure + live-validation entry
- [x] 01.1-retro.md — AC-W1-20..23 added
- [ ] Wave-0 anchor flip — pending founder staging 10× (Track A)
