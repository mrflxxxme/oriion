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
| DV-03 | 01.3 (AC-01.3.7) | BYOK: только plumbing, живой путь = 501-стабы; flag-enforcement не проверен | Live BYOK-путь против реального провайдера + тест enforcement | 02.1-retro | 🔴 open |
| DV-07 | 01.7 | `artifacts.visibility` — stub-колонка (default backfill, не enforced) | Enforcement Option B (private artifacts) + тесты | Wave 2 (02.6 RBAC-расширение) | 🔴 open |
| DV-08 | Wave-0 gate | `internal_demo_passed` — founder staging 10× anchor run не выполнен | `summary.json` + 10× run_NNN.json в `.planning/gates/evidence/wave-0-to-1/` | founder-action (RW-07) | 🔴 open (founder) |
| DV-09 | 00.8 | AC3/AC4 — `npm run e2e:live` (5-route axe + 3-agent demo) не прогнан на staging | e2e:live green на staging, evidence в gate wave-0-to-1 | вместе с DV-08 | 🔴 open (founder) |
| DV-10 | 01.4b | Dramatiq+Redis worker-**transport** live-прогон (Linux) — memory-extraction проверена in-process, не через реальный транспорт | Live worker-транспорт прогон на Docker-стенде | 02.1-retro | 🟡 open |
| DV-11 | 01.9b | Live connector round-trip (telegram-bot / yandex-disk / imap-smtp против реального API) — коннекторы построены + mock-проверены, но не прогнаны на живых кредах | `pytest -m live` connector suite при кредах в каноне `.env` (TG bot-token RW-03, Yandex Disk OAuth, IMAP/SMTP RW-01) | 02.1-retro (по мере кредов; остаток — вместе с 02.3 live-proof) | 🔴 open (gated) |
| DV-13 | 01.10 (review-gate) | Полная 30-task golden-сертификация вертикалей: review-run DV-02/DV-12 прогонял выборку из 5 задач; полный датасет (30+5 adversarial × 2 вертикали) с порогом ≥75% не прогнан | Evaluator-run полных датасетов на live DeepSeek, отчёты в `.planning/verticals/*/review-artifacts/` | 02.4 (W2) | 🔴 open |
| DV-14 | grill-2026-07-15 (D-34) | `ac_ids`↔спека **двусторонняя** сверка не реализована: `verify_evidence.py` v2 требует наличие `ac_ids` и валидирует форму, но НЕ проверяет, что (а) каждый id существует в AC-таблице спеки и (б) каждый evidence-проверяемый AC спеки назван хоть одним PASS-артефактом. Пока агент может назвать несуществующий AC или умолчать о непокрытом | Парсинг AC-таблицы спеки фазы + сверка в обе стороны, тесты на оба направления | 02.1-retro | 🟡 open |
| DV-15 | grill-2026-07-15 (D-34) | Контракт `kind: wiring` объявлен, но не принуждается: схема не требует `kind` и ничто не проверяет, что AC про рантайм-поведение закрыт именно wiring-, а не quality-артефактом. Классификация AC («утверждает ли он рантайм-поведение») машинно не выводится — нужен явный маркер в спеке | Маркер в AC-таблице (напр. колонка `runtime: yes`) + требование `kind: wiring` для таких AC в `verify_evidence.py` | 02.1-retro | 🟡 open |

## Закрытые записи

| ID | Закрыто | Как |
|---|---|---|
| DV-02 | 01.10 (review-gate) | **Live review-run 2026-07-09 + founder-approved.** Master-prompt `agency_marketing_ru` promoted `draft → reviewed` (`.planning/contracts/role-prompts/masters/agency_marketing_ru.md`, `status: reviewed`, `version: 1.0.0`, `quality_bar: stable`). Live plan+synthesis on funded DeepSeek + 5/5 adversarial probes SAFE; deliverables reviewed-quality (approve-worthy); founder APPROVED the vertical. Review package: `.planning/verticals/agency-marketing-ru/review-artifacts/REVIEW-PACKAGE.md`. |
| DV-12 | 01.10 (review-gate) | **Live review-run 2026-07-09 + TG-008 anti-fabrication fix + re-run 2026-07-10 + founder-approved.** Master-prompt `telegram_creator` promoted `draft → reviewed` (`.planning/contracts/role-prompts/masters/telegram_creator.md`, `status: reviewed`, `version: 1.0.0`, `quality_bar: stable`). Live review: 5/5 adversarial SAFE, 4/5 reviewed-quality; the single defect (TG-008 post-draft case-study **fabricated metrics**) was hardened at the horizontal **writer** role-prompt (zero-fabrication output-discipline, `writer.md` v1.0.0→v1.1.0) and TG-008 re-run through plan→synthesis on live DeepSeek — deliverable now uses ONLY the supplied facts (+40% / 2 месяца), explicitly disclaims guaranteed repetition, no invented ₽/ROI/extra metrics. Founder APPROVED. Review package: `.planning/verticals/telegram-creator/review-artifacts/REVIEW-PACKAGE.md`. |
| DV-04 | 01.9a | Оба флага (`security_dlp_enabled`, `security_injection_scan_enabled`) → **default True** в `backend/src/_shared/config.py`; тест дефолтов `backend/tests/security/test_security_flags_default.py`; success-path не ломается, реальный ПДн блокируется — `backend/tests/security/test_dlp_activation_pipeline.py`. Precision-предусловие закрыто через DV-05. |
| DV-05 | 01.9a | Context-aware INN-10 (checksum **И** «ИНН»-контекст в окне 40 симв.) в `backend/src/security/detectors/pii.py`; golden-корпус `backend/tests/security/corpus/`; precision-тест `backend/tests/security/test_inn_precision.py` — baseline FP 100% (hard) / ~10% (random) → tuned **0% ≤ 1%**; recall на контекстных positives = 1.0 (`test_inn_recall.py`). |
| DV-06 | 01.8-mail | **Live-send прогнан на staging (VPS Timeweb) 2026-07-09.** Реальный `YandexSmtpEmailSender` (`is_smtp_configured=True`, host `smtp.yandex.ru`, implicit TLS 465) подключился, аутентифицировался (прежняя `535` устранена) и Yandex **принял** verification-письмо → доставлено на `profiki.ai@yandex.com` (лог `smtp email sent kind=verification`). Креды — в `infra/vps-minimal.env` (RW-01 🟢). |

## Протокол

1. **Добавление:** фаза, закрывающая AC частично, добавляет строку в том же PR (reviewer-роль проверяет).
2. **Погашение:** запись переводится в «Закрытые» только с ссылкой на evidence (тест-ран / evidence-артефакт / merged PR).
3. **Гейт волны:** wave-гейт не проходит при открытых записях класса P1 (утечка/деньги/auth), адресованных закрываемой волне.
4. **Retro-фаза:** `NN.1-retro` каждой волны начинает с прохода по этому реестру.
