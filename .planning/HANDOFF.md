# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией (Exit ritual). История — `git log HANDOFF.md`.

## Last updated
- Date: 2026-07-10
- Session: `/autonomy:run` 01.8c (PR-1 merged) → chip 01.8c-rename (PR-2, brand=profiki)
- Agent: @claude (autonomous runner, ADR-037/040)

## 01.8c — ПОЛНОСТЬЮ завершена (2 PR)
- **PR-1 (autonomy dev-infra) — MERGED #109 `857e09d`:** нативные ролевые сабагенты (D8), OpenAPI-snapshot+drift-CI (D2), docs-freshness CI (D9), JOURNAL-архивация (D12). Founder in-session ack (public_api_contracts). main HEALTHY.
- **PR-2 (brand-rename teamly→profiki, D3) — code-complete, ack-needed:** OQ-09 решён founder = **profiki**.
  - **Scope-решение founder:** только `teamly→profiki` (потребительский бренд, 18→ файлов); `oriion` **оставлен внутренним codename** (JWT iss/aud, RLS-роль `oriion_app`, CloudEvents-namespace, бакеты/сервисы — 0 functional identifiers тронуто; oriion→profiki = отдельная рискованная инфра-миграция, НЕ сделана).
  - **Формы:** Cyrillic **«Профики»** в UI (email/`<title>`/промпты) + Latin **`Profiki`/`profiki`** в коде/пакетах/доменах.
  - 74 замены / 29 файлов; 6 role-prompts + PATCH SemVer + test-pins lockstep; uv.lock + openapi.snapshot regen.
  - **Carve-outs:** `oriion`, `@teamly-ai` (author-conv, ADR-027), `teamly.to` (внешний реф), memory-file-name, immutable ADR/AUDIT/JOURNAL, filesystem `TEAMLY_RU`.
  - Гейты: ruff/format/mypy 241/bandit 0/**unit 1162**/openapi-fresh; **golden-smoke 7/7 PASS** (~$0.016). Tripwire `auth_rbac_sessions`+`public_api_contracts` → **ack-needed**.

## Founder actions
1. **Ack PR-2** (tripwire iam+contracts; brand-rename, oriion internal preserved) → merge.
2. **Wave-1 formal closure** (всё за founder): vertical review draft→reviewed (DV-12/02 — уже promoted #110?), cost/risk review, подпись `gates/wave-1-to-2`.
3. **Parked фазы (нужны креды):** 01.3b ЮKassa (RW-04) · 01.8b OAuth (RW-02) · 01.11 TG-Business (RW-05). Drop creds → «RW-0N ready» → unpark.
4. **Chips:** `task_dd666049` (PreToolUse hook — role tool-scope enforcement, SECURE-P2) · (rename chip `task_4e7f04db` — закрыт этим PR-2).

## Gate commands (no `make`; use subshells `(cd backend && …)` — armed premerge-hook брикует cwd вне root/backend)
backend: `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` · `uv run bandit -r src -c pyproject.toml` · `uv run python ../scripts/autonomy/export_openapi.py --check`. autonomy (root): `python scripts/autonomy/check_subagents.py` · `check_docs_freshness.py`. golden: `PYTHONIOENCODING=utf-8 uv run python scripts/live_golden_master.py`.

## Read first
README · this HANDOFF · PROJECT-STATE · STATUS · `agent-handbook/00-START-HERE.md` · runner contracts (DoR + FOUNDER-RUNWAY + DEFERRED-VERIFICATION).
