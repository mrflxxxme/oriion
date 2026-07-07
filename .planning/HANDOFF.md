# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-07 (docs-refinement: founder-интервью → ADR-040 spec-contract автономного исполнения)
- Session: `docs-refinement-interview` (branch `claude/docs-refinement-interview-z4soj2`)
- Agent: @claude (remote session, интерактивное founder-интервью)

## Project status

- **Wave:** Wave 1 (Core MVP), смержено всё до 01.8 включительно (`origin/main = 0c1e9fc`).
- **Эта сессия:** документационная (0 строк кода). Углублённое интервью с founder → 12 решений → [ADR-040](./decisions/ADR-040-execution-spec-contract.md) + новые нормативные артефакты + актуализация дрейфнувших доков.

## What just happened

Вход: три параллельных исследования (методология+автономный контур / roadmap / код-vs-доки) выявили 10 разрывов, мешающих точному автономному исполнению дорожной карты. Интервью (3 раунда × 4 вопроса, по каждому — анализ и рекомендация) зафиксировало решения; всё внесено в канон.

### Новые нормативные документы

| Документ | Что это |
|---|---|
| [`decisions/ADR-040-execution-spec-contract.md`](./decisions/ADR-040-execution-spec-contract.md) | 12 решений интервью (D1–D12), Accepted |
| [`roadmap/DEFINITION-OF-READY.md`](./roadmap/DEFINITION-OF-READY.md) | 11-пунктовый DoR; `/autonomy:run` не исполняет фазу без `DoR: PASS` в PLAN.md |
| [`DEFERRED-VERIFICATION.md`](./DEFERRED-VERIFICATION.md) | Реестр мягких AC (DV-01..DV-10); мягкий AC без записи = блокирующий review-flag; гасятся обязательными `NN.1-retro` |
| [`FOUNDER-RUNWAY.md`](./FOUNDER-RUNWAY.md) | Манифест founder-зависимостей (RW-01..RW-09); раннер паркует гейтед-фазы на preflight |
| Seed-specs `roadmap/wave-1-core-mvp/phases/{01.8c,01.9,01.4-ui,01.10,01.12}-*.md` | Констрейнты всех оставшихся W1-фаз; **01.8c autonomy-hardening — новая сервисная фаза** (роли→нативные сабагенты, OpenAPI-snapshot+CI, docs-freshness CI, код-ренейм Oriion) |

### Ключевые изменения существующего канона

- **Гейт W1→2 переписан** (`gates/wave-1-to-2.md`): чисто технические пороги (AC pass-rate ≥0.9 + must-фазы merged + DV-clean); прежний кодировал до-2026-05-15 скоуп («5 вертикалей, 10 фаз, NPS≥30») и был невычислим. Friend-валидация → **W2 фаза 02.0** (неблокирующая), NPS — измерение, не порог.
- **Очередь W1 (ADR-040 D4):** `01.8c → 01.9 → 01.4-ui → 01.10 → 01.12`; must-закрытие волны = 01.9+01.4-ui+01.10+01.12; 01.3b/01.8b/01.11 = 🅿️ Parked (RW-04/02/05), волну НЕ держат.
- **`run.md`/`discuss.md`:** RUNWAY-preflight, DoR-gate перед execute, budget v3 ($20 soft → доводим фазу и паркуем очередь / $40 hard → stop), live-goldens только по контрольной ценности, doc-sync в exit-ритуале (README-фаза, runbook, статус фазного файла, sync гейтов при реорге).
- **`cost-budget.yaml` → v3** (per-day 20/40, было 30/75 — founder-поправка к рекомендации).
- **`tripwire.yaml`:** D2-нюанс — охраняемый контракт = будущий `.planning/contracts/openapi.snapshot.json` (реализация 01.8c; текущий глоб fail-safe покрывает).
- **DLP (ADR-040 D10):** precision (ИНН FP ≤1%) → оба флага ON → только потом первый MCP-коннектор; блокирующий AC фазы 01.9.
- **Ребрендинг:** рабочее имя **Oriion** (OQ-09 обновлён); README/CONTRIBUTING/Makefile переименованы + README-статус актуализирован (застыл на «Phase 00.1»); CONTRIBUTING tier-table приведён к ADR-037. Код-ренейм (main.py, тесты, role-prompts + SemVer bump) — в 01.8c, НЕ здесь.
- Гигиена D12: статусы 00.5/00.8 синхронизированы; wave-0-to-1 gate проза = фронтматтер; ADR-index +038/039/040.

## In progress / not done (deliberately)

- **Реализация** snapshot-CI / docs-freshness CI / RUNWAY-preflight-скрипта / нативных сабагентов — всё это **фаза 01.8c** (seed-spec готов); данный PR — только документы и нормативка.
- JOURNAL.md >170KB — архивация в `dev-log/archive/` внесена в scope 01.8c (maintenance).
- RUN-QUEUE не трогался (нет блокирующих записей).

## Next steps

1. Founder: merge этого PR (docs-only; правка `cost-budget.yaml` попадает под glob `secrets_keys_crypto` → ожидаем 1-click ack).
2. `/autonomy:run 01.8c` — далее очередь по ADR-040 D4 автоматически.
3. Founder (параллельно, по желанию): разблокировки RW-01 (SMTP) / RW-03 (bot-token — дёшево, держит вторую вертикаль) / RW-07 (staging anchor run — закрывает Wave 0 формально).

## Next agent — read first

1. [`README.md`](./README.md) — what is this project
2. **this HANDOFF.md** — snapshot
3. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol
4. Новые обязательные контракты раннера: [`roadmap/DEFINITION-OF-READY.md`](./roadmap/DEFINITION-OF-READY.md) + [`FOUNDER-RUNWAY.md`](./FOUNDER-RUNWAY.md) + [`DEFERRED-VERIFICATION.md`](./DEFERRED-VERIFICATION.md) (per `run.md` §Contracts п.4).

## Exit ritual completed (this session)

- [x] ADR-040 + DoR + DEFERRED-VERIFICATION + FOUNDER-RUNWAY + 5 seed-specs written
- [x] Gates wave-1-to-2 (rewrite) + wave-0-to-1 (prose sync) updated
- [x] run.md / discuss.md / cost-budget.yaml v3 / tripwire.yaml updated
- [x] JOURNAL.md entry appended (2026-07-07)
- [x] HANDOFF.md rewritten (this file)
- [x] Doc-sync per ADR-040 D9: README status actual · phase-file statuses synced · gate-files synced in the same PR
- [ ] PR opened — this session's closing action (draft, tripwire ack expected)
