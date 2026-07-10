# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией (Exit ritual). История — `git log HANDOFF.md`.

## Last updated
- Date: 2026-07-10
- Session: `/autonomy:run` — **Wave-1 formal close** (подпись гейта wave-1-to-2 по поручению founder)
- Agent: @claude (autonomous runner, ADR-037/040)

## 🏁 WAVE 1 (Core MVP) — ФОРМАЛЬНО ЗАКРЫТА (gate PASS, 2026-07-10)

Гейт [`gates/wave-1-to-2.md`](./gates/wave-1-to-2.md) подписан (`status: PASS`, `founder_signature` set, `closed_at: 2026-07-10`) по прямому in-session-поручению founder: **«Подпиши за меня Wave 1 — согласовано»**. Раннер перед подписью перепроверил (не штамповал):
- **`acceptance_criteria_pass_rate ≥ 0.9`** → MET (~1.0): все must-фазы merged с зелёными CI-гейтами + phase-evidence (01.9a/01.9b adversarial PASS, 01.10 live-golden 7/7, 01.8c golden-smoke 7/7). Founder-waived провалов нет.
- **`must_phases_merged`** → MET: 01.9a+01.9b · 01.4-ui · 01.10 · 01.12 + 01.8c (PR-1 #109 + PR-2 #111 ренейм + #112 SECURE-hook + #113 docfix) на `main` (`85059a6` HEALTHY) + VPS-verified. Обе вертикали (`telegram_creator` + `agency_marketing_ru`) — `reviewed` (DV-02/DV-12 закрыты).
- **`deferred_verification_clean`** → MET: нет открытых DV класса P1 (leak/money/auth), адресованных Wave 1. DV-04/05/06 закрыты; открытые DV-11/01/03/10/07 — non-P1, cred/quality-gated, переезжают в Wave 2.

**Deliverables:** D1/D2/D3 ✅ · D4 ✅ (cost-budget v3→v4 $50/$75, founder-directed) · D5 ✅ (light risk pass — без новых блокеров) · **D6 ⏸ DEFERRED** (Wave-2 PHASES-регенерация + seed-specs) — сознательно в отдельную сессию по поручению founder.

## Что дальше (следующая сессия — планирование Wave 2)
1. **`/autonomy:run` планирование Wave 2** (D6): регенерировать [`roadmap/wave-2-pixel-catalog/PHASES.md`](./roadmap/wave-2-pixel-catalog/README.md) + seed-specs per DoR + синхронизировать `gates/wave-2-to-3.md` (ADR-040 D1/D5). Обязательный старт: **02.1-retro** (гашение DV-01/03/10/11) + **02.0 friend-validation** (NPS **измеряется**, не порог).
   - Учесть дельты Wave-1-факта: бренд «Профики»/`Profiki` (oriion — internal); auth email-only (OAuth descoped); коннекторы = native-tool (ADR-041), реальный MCP-протокол = развилка 02.4; обе вертикали уже reviewed (WB — единственная под полный первый цикл research→draft→review).
2. **Parked → Wave 2** (распарк по мере кредов): 01.3b ЮKassa (RW-04, внешний счёт 5–10 дн) · 01.11 Telegram Business (RW-05, юрист). **01.8b OAuth — descoped** (не переносится).
3. **Cred-gated live-verify (DV-11):** как только founder положит Telegram bot-token (RW-03) / Yandex-Disk OAuth / IMAP-креды в git-ignored env → прогнать `pytest -m live` connector-suite (round-trip против реального API).
4. **Открытый product-вопрос (не блокер):** «email-only» оставил пароль + 2FA-TOTP как email-based опции; если нужно строго «только magic-link» — отдельное продуктовое решение founder.

## Gate commands (no `make`; use subshells `(cd backend && …)` — armed premerge-hook брикует cwd вне root/backend)
backend: `uv run ruff check/format --check src tests` · `uv run mypy --strict src` · `uv run pytest -m "not integration"` · `uv run bandit -r src -c pyproject.toml` · `uv run python ../scripts/autonomy/export_openapi.py --check`. autonomy (root): `python scripts/autonomy/check_subagents.py` · `check_docs_freshness.py` · `check_main_health.py`. golden: `PYTHONIOENCODING=utf-8 uv run python scripts/live_golden_master.py`.

## Read first
README · this HANDOFF · PROJECT-STATE · STATUS · `agent-handbook/00-START-HERE.md` · [`gates/wave-1-to-2.md`](./gates/wave-1-to-2.md) (закрыт) · runner contracts (DoR + FOUNDER-RUNWAY + DEFERRED-VERIFICATION).
