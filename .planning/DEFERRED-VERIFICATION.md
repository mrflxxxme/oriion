# DEFERRED-VERIFICATION — реестр отложенной верификации

> Единый реестр «мягких» acceptance criteria per [ADR-040 D6](./decisions/ADR-040-execution-spec-contract.md).
> Правило: AC, закрытый частично (stub-level / plumbing-only / flag-OFF / live-проверка отложена),
> **обязан** иметь запись здесь ДО merge своей фазы — иначе блокирующий review-flag.
> Погашение: первая фаза каждой волны — `NN.1-retro` — закрывает записи, адресованные этой волне.
> Запись закрывается только evidence-фактом (тест / live-golden / включённый флаг), не словами.

## Формат

`DV-NN | фаза-источник | что НЕ доказано | чем доказывается | фаза-погашение | статус`

## Активные записи

| ID | Источник | Что не доказано | Чем доказывается | Погашение | Статус |
|---|---|---|---|---|---|
| DV-01 | 01.2 (AC-3.6) | Реальный пайплайн `resolve_master→DB→MasterAgent` — automated-проверка была stub-level | Live golden Master end-to-end на funded DeepSeek (уже прогнан 7/7 как F1-before-01.4 — нужна фиксация evidence-артефакта в каноне) | 02.1-retro | 🟡 open (частично прогнан, evidence не закреплён) |
| DV-02 | 01.2 (AC-3.7) | Master-prompt `agency_marketing_ru` promotion `draft → reviewed` (evaluator-run + founder review per ADR-026) | Evaluator-run на golden-dataset ≥75% + adversarial 100% + подписанный REVIEW-CHECKLIST | 01.10 (вместе со второй вертикалью) | 🔴 open |
| DV-03 | 01.3 (AC-01.3.7) | BYOK: только plumbing, живой путь = 501-стабы; flag-enforcement не проверен | Live BYOK-путь против реального провайдера + тест enforcement | 02.1-retro | 🔴 open |
| DV-06 | 01.8-mail | Live-send реального SMTP не прогнан (нет кредов) | `pytest -m live` iam email suite при SMTP-кредах в каноне (см. RUNWAY RW-01) | по разблокировке RW-01 | 🔴 open (gated) |
| DV-07 | 01.7 | `artifacts.visibility` — stub-колонка (default backfill, не enforced) | Enforcement Option B (private artifacts) + тесты | Wave 2 (02.6 RBAC-расширение) | 🔴 open |
| DV-08 | Wave-0 gate | `internal_demo_passed` — founder staging 10× anchor run не выполнен | `summary.json` + 10× run_NNN.json в `.planning/gates/evidence/wave-0-to-1/` | founder-action (RW-07) | 🔴 open (founder) |
| DV-09 | 00.8 | AC3/AC4 — `npm run e2e:live` (5-route axe + 3-agent demo) не прогнан на staging | e2e:live green на staging, evidence в gate wave-0-to-1 | вместе с DV-08 | 🔴 open (founder) |
| DV-10 | 01.4b | Dramatiq+Redis worker-**transport** live-прогон (Linux) — memory-extraction проверена in-process, не через реальный транспорт | Live worker-транспорт прогон на Docker-стенде | 02.1-retro | 🟡 open |
| DV-11 | 01.9b | Live connector round-trip (telegram-bot / yandex-disk / imap-smtp против реального API) — коннекторы построены + mock-проверены, но не прогнаны на живых кредах | `pytest -m live` connector suite при кредах в каноне `.env` (TG bot-token RW-03, Yandex Disk OAuth, IMAP/SMTP RW-01) | по разблокировке кредов (founder предоставит отдельно) | 🔴 open (gated) |
| DV-12 | 01.10 | telegram_creator full certification: golden ≥75% на 30-task golden-dataset + adversarial 100% + `draft → reviewed` promotion (REVIEW-CHECKLIST) — прогнан только lean live-golden 7/7 (plan+synthesis contract + 5 adversarial), не полный 30-task judge-scored evaluator | Full evaluator-run на 30-task golden ≥75% + adversarial 100% + подписанный founder REVIEW-CHECKLIST (вместе с DV-02 agency_marketing_ru — тот же review-gate) | founder review-gate (планируемый ack) | 🟡 open (lean-proven) |

## Закрытые записи

| ID | Закрыто | Как |
|---|---|---|
| DV-04 | 01.9a | Оба флага (`security_dlp_enabled`, `security_injection_scan_enabled`) → **default True** в `backend/src/_shared/config.py`; тест дефолтов `backend/tests/security/test_security_flags_default.py`; success-path не ломается, реальный ПДн блокируется — `backend/tests/security/test_dlp_activation_pipeline.py`. Precision-предусловие закрыто через DV-05. |
| DV-05 | 01.9a | Context-aware INN-10 (checksum **И** «ИНН»-контекст в окне 40 симв.) в `backend/src/security/detectors/pii.py`; golden-корпус `backend/tests/security/corpus/`; precision-тест `backend/tests/security/test_inn_precision.py` — baseline FP 100% (hard) / ~10% (random) → tuned **0% ≤ 1%**; recall на контекстных positives = 1.0 (`test_inn_recall.py`). |

## Протокол

1. **Добавление:** фаза, закрывающая AC частично, добавляет строку в том же PR (reviewer-роль проверяет).
2. **Погашение:** запись переводится в «Закрытые» только с ссылкой на evidence (тест-ран / evidence-артефакт / merged PR).
3. **Гейт волны:** wave-гейт не проходит при открытых записях класса P1 (утечка/деньги/auth), адресованных закрываемой волне.
4. **Retro-фаза:** `NN.1-retro` каждой волны начинает с прохода по этому реестру.
