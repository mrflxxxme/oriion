# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией (Exit ritual). История — `git log HANDOFF.md`.

## Last updated
- Date: 2026-07-09
- Session: `/autonomy:run` — Wave-1 completion (budget v4 $50/$75)
- Agent: @claude (autonomous runner, ADR-037/040)

## Wave-1 status — MUST-SET CODE-COMPLETE + VPS-VERIFIED
`origin/main` = `ce83ed2`. Все must-фазы смержены + задеплоены + проверены на VPS `staging.профики.online`:
**01.9a** DLP (#95) · **01.9b** connectors (#99) · **01.4-ui** memory panel (#94) · **01.10** telegram_creator (#100) · **01.12** dashboard+onboarding (#103). Плюс: budget-cap v4 (#97), evidence-lifecycle fix (#98), D7 heal ×2 (#101/#102), run-bookkeeping (#96), wave-close (#104). **Итоговая справка: [`roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md`](./roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md)** · rolling: [`PROJECT-STATE.md`](./PROJECT-STATE.md).

**Server-verified (2026-07-09):** DLP-флаги ON в проде; capability-gate режет send / пускает read; миграция `connector_credentials` (mcp/0002) применена; маршруты `/memory` `/dashboard` `/onboarding` → 200; healthz ok. Live-golden 01.10 telegram_creator 7/7.

## Remaining to FORMALLY close Wave 1 — все FOUNDER-действия (код готов)
1. **Обзор вертикалей draft→reviewed** (telegram_creator + agency_marketing_ru) → подпись REVIEW-CHECKLIST — закрывает DV-12 + DV-02 + порог гейта «2nd vertical reviewed». Полный 30-task golden≥75% cert прогоняется на этом гейте.
2. **Cost-budget review** (v4 50/75) + **risks review** + **founder_signature** на [`gates/wave-1-to-2.md`](./gates/wave-1-to-2.md) (autonomous-вычислимые пороги уже отмечены MET).
3. **Креды (отдельно):** RW-03 Telegram bot-token · RW-01 SMTP/IMAP · Yandex Disk OAuth → закрывает DV-11 (connector live-smoke) + 01.10 live Bot-API demo + DV-06 (SMTP live-send).
4. (Опц.) RW-07 staging anchor-run — формально закрывает Wave 0 (DV-08/09).
5. **Wave-2 setup:** regenerate `roadmap/wave-2-pixel-catalog/PHASES.md` seed-specs (incl. 02.0 friend-validation + 02.1-retro).

## Self-acks this run (founder-authorized «продолжай до конца волны»; reviewable)
#99 (db_migrations pure-CREATE + secrets_keys_crypto) · #100 (public_api_contracts additive) · #97 (budget-cap). Все с анализом в RUN-QUEUE + PR-body + JOURNAL.

## Open follow-ups (later)
- **AC-W1-25 — УЖЕ СДЕЛАНО** (не открытый долг): shipped PR #44 / commit 799e259 (4 горизонтальных промпта v1.0.0 с ≥2 non-brief §6 примерами + drift-fixture `test_role_prompt_diversity.py`). Chip task_69d1e107 был устаревшим.
- **01.9b deferred security** (до включения autonomous send — Wave-2+; 01.12-поверхности read-only): fail-open scoping → fail-closed; layer-B PII → layer-A ML.
- **01.8c** (dev-infra: native subagents, OpenAPI-snapshot CI, docs-freshness CI, Oriion code-rename) — post-wave, не в must-set.

## Методология (обновлено 2026-07-09, founder-директива)
`run.md` exit-ritual §6e = **phase state-summary** каждой фазы (continuous → `PROJECT-STATE.md`); stop-conditions = **wave state-summary** на закрытии волны (`WAVE-N-SUMMARY.md`). Формат — [`_meta/state-summary-template.md`](./_meta/state-summary-template.md).

## Gate commands (no `make` on Windows)
backend: `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` (per-module `--cov-fail-under=85` per subtree) · `uv run bandit -r src -c pyproject.toml`. frontend: `npm run lint/format:check/typecheck/test`. Deploy: manual (memory `teamly-vps-deploy-verify`).

## Read first
README · this HANDOFF · WAVE-1-SUMMARY · `agent-handbook/00-START-HERE.md` · runner contracts (`DEFINITION-OF-READY.md` + `FOUNDER-RUNWAY.md` + `DEFERRED-VERIFICATION.md`).
