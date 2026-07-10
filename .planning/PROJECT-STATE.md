# PROJECT-STATE — rolling состояние проекта

> Непрерывный накопитель phase state-summary'ев (founder-директива 2026-07-09; `run.md` exit-ritual §6e).
> Каждая завершённая фаза **prepend**'ит сюда свою справку (2 блока: техническое состояние + пользовательские
> сценарии; формат — [`_meta/state-summary-template.md`](./_meta/state-summary-template.md)). Полные картины
> волн — в `roadmap/<wave>/WAVE-N-SUMMARY.md`. Свежее — сверху.

---

## Текущий срез: Wave 1 (Core MVP) — ✅ ЗАКРЫТА (gate PASS, 2026-07-10)

Гейт [`wave-1-to-2`](./gates/wave-1-to-2.md) подписан (`status: PASS`, 2026-07-10) по прямому поручению founder («Подпиши за меня Wave 1 — согласовано»). Все три вычислимых порога MET (AC pass-rate ~1.0 · must-фазы merged · DEFERRED-VERIFICATION без открытых P1). Обе вертикали `reviewed`; инфра-долг (01.8c) + brand-rename закрыты; `main` HEALTHY, задеплоено + VPS-verified.
Полная справка волны → [`roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md`](./roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md).
**Next:** планирование Wave 2 — отдельная сессия (обязательный старт: 02.1-retro гашение DV + 02.0 friend-validation). Parked → Wave 2: 01.3b (RW-04) · 01.11 (RW-05); 01.8b OAuth — descoped.

---

## Phase deltas (свежее сверху)

### 01.8c PR-2 — brand-rename teamly→profiki / «Профики» (2026-07-10, D3)
- **Тех:** OQ-09 решён (founder) = **profiki**. Переименован потребительский бренд: 74 замены / 29 файлов — **Cyrillic «Профики»** в user-facing (email-темы/тело, `<title>`, демо-промпты) + **Latin `Profiki`/`profiki`** в коде/пакетах/доменах (API title, `profiki-backend`/`profiki-frontend`, TOTP issuer, `profiki.online`). Роль-промпты (6) переименованы + PATCH SemVer-бамп + test-pins в lockstep. Регенерированы `uv.lock` (`profiki-backend`) + `openapi.snapshot.json` (title `Profiki Backend`). **Scope-решение founder:** `oriion` оставлен ВНУТРЕННИМ codename (JWT iss/aud, RLS-роль `oriion_app`, CloudEvents-namespace, бакеты/сервисы — 0 functional identifiers тронуто; ренейм oriion→profiki = отдельная рискованная инфра-миграция, не сделана). Carve-outs: `@teamly-ai` author-конвенция, `teamly.to` внешняя ссылка, memory-file-name, immutable ADR/AUDIT/JOURNAL. Гейты: ruff/format/mypy **241**/bandit 0/**unit 1162**/openapi `--check` fresh. **Golden-smoke 7/7 PASS** (live DeepSeek, agency_marketing_ru master+горизонтали, ~$0.016). Tripwire: **auth_rbac_sessions**(iam email/TOTP) + **public_api_contracts**(prompts+snapshot) → ack-needed.
- **Сценарий:** пользователь видит бренд **«Профики»** во всех точках контакта (email-подтверждения/сброс/magic-link, заголовок вкладки, приветствия агентов) — вместо прежнего «TEAMLY_RU». Инфраструктура (auth-токены, RLS, события) не затронута — деплой/сессии стабильны.

### 01.8c — Autonomy / dev-infra hardening (2026-07-10, PR-1 of 2) — сервисная фаза
- **Тех:** 11 персистентных ролей → нативные спавнабельные сабагенты `.claude/agents/<role>.md` (ADR-040 D8, тонкий spawn-entry + указатель на хендбук) + conformance-гейт `check_subagents.py`; **OpenAPI-snapshot** `contracts/openapi.snapshot.json` (64 маршрута) + `export_openapi.py --check` drift-гейт в ci-backend (D2); **docs-freshness** `check_docs_freshness.py` + workflow `ci-autonomy.yml` (D9, поймал+починил stale-статусы 01.6/01.7); 10× `api.yaml` → non-normative header; **JOURNAL-архивация** D12 (189→46KB, 28 записей → `dev-log/archive/`, content-verified 46=46). Гейты: ruff/format/mypy **241**+3 scripts/bandit 0/unit **1160**/tooling **15**. Adversarial-аудит 3 линзы. Tripwire: `public_api_contracts` (contracts/, additive) → ack-needed.
- **Сценарий:** нет прямого user-facing изменения (сервисная фаза автономного контура). Включает для будущих фаз: judge-panel/reviewer-линзы спавнят **реальные независимые сабагенты**; публичный контракт растягивается **машинно** (snapshot vs живой FastAPI); доки защищены от дрейфа CI-проверкой. Фундамент к старту Wave 2.
- **Отложено:** Oriion-ренейм кода/промптов (D3) → **PR-2 `01.8c-rename`** (тот же ран). Parked (нужны founder-креды): 01.3b (RW-04) · 01.11 (RW-05); 01.8b OAuth — descoped (auth email-only, RW-02 снята).

### 01.12 — Dashboard + Onboarding (2026-07-09, PR #103) — WAVE-1 CLOSER
- **Тех:** frontend `features/{dashboard,onboarding}` + api-клиенты (billing/artifacts/teams); backend `team_provisioning_service` 3-way preset-routing (`src/agents`). Гейты: agents 90 / frontend 201 / mypy 241. Auto-merge. Задеплоено+verified (routes 200).
- **Сценарий:** пользователь проходит register → онбординг-визард (выбор пресета) → первая задача → результат на Dashboard **без инструкций**.

### 01.10 — вертикаль telegram_creator (2026-07-09, PR #100)
- **Тех:** research-brief (17 источников) + seed + Master/role draft-промпты + 30-task golden + 5 adversarial; live-golden 7/7 (~$0.03). Self-ack (public_api_contracts). ADR-026 §7.
- **Сценарий:** пользователь выбирает вертикаль «Telegram-крейтор» → доменный агент с РФ-спецификой (ФЗ-38/РКН/152-ФЗ). Промпты draft → до founder-review.

### 01.9b — коннекторы read+draft (2026-07-09, PR #99, ADR-041)
- **Тех:** 3 native-tool коннектора + capability-gate активация + KMS creds-store (`connector_credentials`, миграция mcp/0002) + DLP-скрин исходящих аргументов. SECURE-аудит PASS. Self-ack. Задеплоено (миграция применена, gate verified).
- **Сценарий:** substrate — агент может read+draft из Telegram/Диск/IMAP; autonomous-send заблокирован до approval-UI. Live-round-trip = DV-11 (нужны креды).

### 01.9a — DLP-активация (2026-07-09, PR #95)
- **Тех:** context-aware INN (FP 11%→0%, golden-корпус) + оба security-флага ON. Закрыты DV-04/05. SECURE-аудит PASS. Auto-merge. Verified ON на проде.
- **Сценарий:** РФ-ПДн (ИНН/СНИЛС/паспорт/телефон/email) не утекают в выводе агента — защита активна по умолчанию.

### 01.4-ui — панель памяти (2026-07-09, PR #94)
- **Тех:** frontend `features/memory` поверх live `/api/v1/memory/*`. Tripwire-free auto-merge. Verified (route 200).
- **Сценарий:** пользователь видит/ищет/добавляет/удаляет, что помнит команда/агент.
