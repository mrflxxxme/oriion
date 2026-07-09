# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией (Exit ritual). История — `git log HANDOFF.md`. Журнал — `JOURNAL.md`.

## Last updated
- Date: 2026-07-09
- Session: `/autonomy:run` — Wave-1 completion (product-first reorder; budget raised to $50/$75)
- Agent: @claude (autonomous runner, ADR-037/040)

## Project status
- **Wave 1 (Core MVP).** VPS `staging.профики.online` (194.87.187.207) — full stack; DLP ON in prod.
- **Merged this run:** 01.4-ui memory panel (#94) · 01.9a DLP activation (#95) · evidence-lifecycle fix (#98) · budget-cap v4 50/75 (#97) · run-queue/park bookkeeping (#96).
- **01.9b connectors — code-complete + SECURE-audit PASS, PR pending** (branch `claude/auto-01.9b-connectors`).
- **Run queue:** `01.9b (finalizing) → 01.10 → 01.12` → wave close. 01.8c (dev-infra) after.

## 01.9b — Connectors (read+draft) — ready to merge
ADR-041 (native-tool callables, not full MCP-protocol — 00.4 client is a Wave-0 stub; real transport → Wave-2). Two passes:
- **A (security core):** `mcp.connector_credentials` KMS table (workspace-RLS default-deny) + `connector_credential_service` (mirror BYOK) + migration `mcp/0002` (pure-CREATE) + `runtime/tool_gating.py` capability-gate activation (DANGEROUS `send_*` always denied → deny-until-01.12; `tools_allowed` scoping, empty=all-non-DANGEROUS backward-compat) wired into `dispatch.build_leaf_runner`; `agent_archetypes.tools_allowed` first runtime enforcement.
- **B (connectors):** telegram-bot / yandex-disk / imap-smtp — READ + DRAFT tools (READ_ONLY/INTERNAL); `send_*` = DANGEROUS guarded stubs. Outgoing-args DLP screen BEFORE every transport call (exfil guard). Creds via KMS service, graceful no-cred degradation. Hardcoded hosts (can't be aimed at attacker endpoint). `build_connector_tools` NOT yet wired into the live `dispatch_task` path — dormant until a vertical archetype opts in (01.10).
- **SECURE audit: PASS 0 P0/P1.** 2 P3 hygiene fixes folded (secret-in-URL redaction; KMSError→degrade). 2 items DEFERRED to 01.12 (before autonomous send turns on): fail-open scoping → fail-closed; layer-B detector gaps (obfuscated/non-RU PII) → layer-A ML.
- Gates: ruff/format · mypy **240** · bandit 0 · pytest **1119 pass**. Integration (connector RLS + creds round-trip) runs in ci-backend real-PG. Tripwire: **ack-needed** (db_migrations pure-CREATE + secrets_keys_crypto) → **self-acked per founder "продолжай до конца волны"** (analysis in RUN-QUEUE). Live-smoke deferred → **DV-11** (needs TG/Disk/IMAP creds; founder provides separately).

## Next
- **01.10** Telegram-creator vertical (dev autonomous: research-brief + Master-prompt + golden; carries DV-02 prompt-promotion; live-демо → RW-03). Can wire a vertical archetype to the 01.9b connectors' `tools_allowed`.
- **01.12** dashboard + onboarding (frontend, autonomous, server-verifiable; wave closer). Also the home for the 2 deferred 01.9b security-hardening items (fail-closed scoping) since it activates approval-UI/send.
- **Consolidated VPS server-verify** after backend phases: build-images-ghcr → `dc pull && dc up -d` (+`alembic upgrade heads` for the connector_credentials migration) → container-exec checks (migration applied, gate denies send).
- **Wave-1 gate** `gates/wave-1-to-2.md`: AC pass-rate ≥0.9 + must-phases merged + DV-clean-for-wave.

## Gate commands (no `make` on Windows)
backend: `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` · `uv run bandit -r src -c pyproject.toml`. frontend: `npm run lint/format:check/typecheck/test`.

## Read first
README · this HANDOFF · `agent-handbook/00-START-HERE.md` · runner contracts (`DEFINITION-OF-READY.md` + `FOUNDER-RUNWAY.md` + `DEFERRED-VERIFICATION.md`).
