# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual. История — `git log HANDOFF.md`. Журнал — `JOURNAL.md`.

## Last updated
- Date: 2026-07-09
- Session: `/autonomy:run` — Wave-1 completion (product-first reorder)
- Agent: @claude (autonomous runner, ADR-037/040)

## Project status
- **Wave 1 (Core MVP).** `origin/main` = `588934c` (после мержа 01.4-ui #94). VPS `staging.профики.online` (194.87.187.207) — full stack healthy.
- **Run queue (product-first reorder, DECISIONS-LOG `run-2026-07-09`):** `01.4-ui ✅ → 01.9a ✅ → 01.9b → 01.10 → 01.12`; 01.8c (dev-infra) отложена в конец.

## Done this session
1. **01.4-ui — Memory panel** ✅ MERGED (#94, `588934c`). Frontend поверх live `/api/v1/memory/*`. Tripwire-free auto-merge. Server-verify batched → post-01.9 checkpoint.
2. **01.9a — DLP activation** ✅ code-complete + locally verified + SECURE-audit PASS (branch `claude/auto-01.9a-dlp-activation`, PR pending). Context-aware INN-10 (checksum + «ИНН»/Latin `inn`/`tax_id`/`налогоплательщик` контекст, whole-line bidirectional window) → **FP 11%→0%** на 720-строчном golden-корпусе, recall 1.0 (18 positives); INN-12 (natural-person PDn) context-free, caught in every evasion form. Оба security-флага (`security_dlp_enabled`+`security_injection_scan_enabled`) → **default True**. **Closes DV-04 + DV-05.** SECURE adversarial audit (independent spawn, refute-by-default): PASS 0 P0/P1; 5 P2/2 P3 (все org-INN-10 edge, не 152-ФЗ PDn) **folded in** (Latin keys, spelled-out labels, bidirectional window, +7 corpus positives). Gates: ruff/mypy(230)/bandit-0/pytest **1033 pass**/security **86**. Tripwire exit 0 → auto-merge. Evidence: `adversarial_audit` (SECURE PASS).

## Next (this run)
3. **01.9b — connectors** (⏳ NEXT): 3 read+draft native-tool connectors (telegram Bot-API / yandex-disk / imap-smtp) — **NOT full MCP-protocol** (00.4 client = Wave-0 stub; real transport → Wave-2), see planned **ADR-041**. Capability-gate activation (`requires_approval()` on DANGEROUS send-tools = deny-until-01.12) + `agent_archetypes.tools_allowed` enforcement + KMS creds-store (mirror BYOK `byok_service`/`kms_provider`, new `mcp.connector_credentials` workspace-scoped table) + audit-line per external call. **Tripwire → ack-needed** (db_migrations new table + secrets_keys_crypto). **Live-smoke deferred** to RW-01 (SMTP/IMAP) + RW-03 (TG bot-token) — build+mock now (seed «dev-part autonomous with mocks»); DEFERRED-VERIFICATION row.
4. **01.10** Telegram-creator vertical (dev autonomous; live-демо gated RW-03; carries DV-02). **01.12** dashboard+onboarding (closer).
5. **Consolidated VPS server-verify** after 01.9x: build-images-ghcr → `dc pull && dc up -d` (+`alembic upgrade heads`) → verify 01.4-ui panel + DLP-ON pipeline. Deploy = manual (repo `/home/deploy/oriion`, `dc='docker compose --env-file infra/vps-minimal.env -f infra/docker-compose.vps-minimal.yml'`).

## Key facts for next agent
- Gates without `make` (Windows): backend `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` · `uv run bandit -r src -c pyproject.toml`; frontend `npm run lint/format:check/typecheck/test`.
- Discovery map of 01.9 surfaces (MCP client stub, BYOK KMS pattern, capability seam, tools_allowed) — see JOURNAL 2026-07-09 + the connector ADR-041 (to be written in 01.9b).
- Read first: README · this HANDOFF · `agent-handbook/00-START-HERE.md` · runner contracts (`DEFINITION-OF-READY.md` + `FOUNDER-RUNWAY.md` + `DEFERRED-VERIFICATION.md`).
