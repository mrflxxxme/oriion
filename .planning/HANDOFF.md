# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией (Exit ritual). История — `git log HANDOFF.md`.

## Last updated
- Date: 2026-07-09
- Session: `/autonomy:run` — Wave-1 completion (budget $50/$75)
- Agent: @claude (autonomous runner, ADR-037/040)

## Wave-1 status — MUST-SET COMPLETE (code)
All four must-phases merged/ready: **01.4-ui** (#94) · **01.9a** DLP (#95) · **01.9b** connectors (#99) · **01.10** telegram_creator vertical (#100) · **01.12** dashboard+onboarding (this PR). Plus: budget-cap v4 (#97), evidence-lifecycle fix (#98), D7 heal ×2 (#101 FK-isolation + #102 connectors_runner coverage).

`origin/main` = `808a00e` (after 01.10; 01.12 PR pending). Merged this run: #94/#95/#96/#97/#98/#99/#100/#101/#102.

## Remaining to formally close Wave 1
1. **Merge 01.12** (tripwire-free auto-merge) → post-merge health check.
2. **Consolidated VPS server-verify** (founder note #1): build-images-ghcr → ssh `dc pull && dc up -d` + `alembic upgrade heads` (connector_credentials mcp/0002) → verify: DLP flags ON, connector capability-gate denies send, memory panel (01.4-ui) renders, dashboard + onboarding wizard load; run `onboarding.spec.ts @live` (register→wizard→task→artifact→dashboard, ~$0.3-1) OR container-exec checks. Domain `staging.профики.online`.
3. **Wave-1 gate** `gates/wave-1-to-2.md`: AC pass-rate ≥0.9 + must-phases merged + DV-clean-for-wave.
4. Run-complete RUN-QUEUE entry + notify.

## Founder action items (accumulated, non-blocking; deferred per note #5)
- **Vertical review-gate:** review telegram_creator + agency_marketing_ru draft prompts → `reviewed` (DV-12 + DV-02). Full 30-task golden≥75% certification runs at that gate.
- **Creds (provide separately):** RW-03 Telegram bot-token, RW-01 SMTP/IMAP, Yandex Disk OAuth → closes DV-11 (connector live-smoke) + 01.10 live Bot-API demo + 01.8-mail live-send (DV-06).
- **RW-07** staging anchor run (formally closes Wave 0; DV-08/09).
- **Self-acks this run** (all founder-authorized «продолжай до конца волны», in RUN-QUEUE + PR bodies + JOURNAL): #99 (db_migrations pure-CREATE + secrets), #100 (public_api_contracts additive), #97 (budget-cap). Reviewable post-hoc.

## Open follow-ups (chips / later)
- task_69d1e107 — AC-W1-25 horizontal prompt-hardening (diversify few-shot examples).
- **01.9b deferred security** (revisit before autonomous send activates — 01.12 surfaces are read-only): fail-open scoping → fail-closed; layer-B PII → layer-A ML. Track for Wave-2 / a retro.
- **01.8c** (dev-infra: native subagents, OpenAPI-snapshot CI, docs-freshness CI, Oriion code-rename) — NOT in the wave must-set; post-wave.

## Gate commands (no `make` on Windows)
backend: `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` (per-module gates `--cov-fail-under=85` per subtree) · `uv run bandit -r src -c pyproject.toml`. frontend: `npm run lint/format:check/typecheck/test`. Deploy: manual (memory `teamly-vps-deploy-verify`).

## Read first
README · this HANDOFF · `agent-handbook/00-START-HERE.md` · runner contracts (`DEFINITION-OF-READY.md` + `FOUNDER-RUNWAY.md` + `DEFERRED-VERIFICATION.md`).
