# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией (Exit ritual). История — `git log HANDOFF.md`. Журнал — `JOURNAL.md`.

## Last updated
- Date: 2026-07-09
- Session: `/autonomy:run` — Wave-1 completion (product-first; budget $50/$75)
- Agent: @claude (autonomous runner, ADR-037/040)

## Project status
- **Wave 1 (Core MVP).** VPS `staging.профики.online` (194.87.187.207); DLP ON in prod.
- **Merged this run:** 01.4-ui (#94) · 01.9a DLP (#95) · budget-cap (#97) · evidence-fix (#98) · 01.9b connectors (#99) · run bookkeeping (#96).
- **01.10 telegram_creator vertical — code-complete + live-golden 7/7, PR pending** (branch `claude/auto-01.10-telegram-creator`).
- **Remaining to close wave: 01.12** (dashboard+onboarding, frontend, autonomous, server-verifiable). Then consolidated VPS server-verify + wave gate. 01.8c (dev-infra) optional after.

## 01.10 — ready to merge
Second vertical `telegram_creator`: research-brief (17 cited) + seed (`community-manager` archetype wired to 01.9b `telegram_read_updates`/`telegram_draft_message`, send excluded) + Master/role **draft** prompts (SemVer) + 30-task golden + 5 adversarial + ADR-026 §7 (research-first normative). **Live golden 7/7 PASS** (~$0.03; plan+synthesis contract + 5/5 adversarial). Gates green (mypy 241, pytest 1127, bandit 0). Tripwire `public_api_contracts` (new role-prompt, additive) → self-ack. Evidence: `live_golden`.
- **Deferred (founder review-gate, planned ack):** DV-12 full 30-task golden≥75% certification + `draft→reviewed` promotion (telegram_creator) + DV-02 (agency_marketing_ru) — same review. Present prompts + golden to founder.
- **Follow-ups:** AC-W1-25 horizontal prompt-hardening (chip); live Bot-API demo → RW-03.

## Founder action items (accumulated, non-blocking)
- **Vertical review-gate:** review telegram_creator + agency_marketing_ru draft prompts → `reviewed` (DV-12 + DV-02).
- **Creds for live verification (provide separately):** RW-03 Telegram bot-token, RW-01 SMTP/IMAP, Yandex Disk OAuth → closes DV-11 (connector live-smoke) + 01.10 live Bot-API demo + 01.8-mail live-send (DV-06).
- **RW-07** staging anchor run (formally closes Wave 0; DV-08/09).

## Next (this run)
- **01.12** dashboard + onboarding (frontend feature over live APIs; tripwire-free auto-merge; server-verifiable like 01.4-ui). Also the home for 01.9b's 2 deferred security items (fail-closed scoping) since it activates approval-UI.
- **Consolidated VPS server-verify:** build-images-ghcr → `dc pull && dc up -d` (+`alembic upgrade heads` for connector_credentials) → container-exec checks (migration applied, capability gate denies send, memory panel + dashboard render).
- **Wave-1 gate** `gates/wave-1-to-2.md`: AC pass-rate ≥0.9 + must-phases merged + DV-clean-for-wave.

## Gate commands (no `make` on Windows)
backend: `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` · `uv run bandit -r src -c pyproject.toml`. frontend: `npm run lint/format:check/typecheck/test`.

## Read first
README · this HANDOFF · `agent-handbook/00-START-HERE.md` · runner contracts (`DEFINITION-OF-READY.md` + `FOUNDER-RUNWAY.md` + `DEFERRED-VERIFICATION.md`).
