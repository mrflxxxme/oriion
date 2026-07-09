# PROJECT-STATE — rolling состояние проекта

> Непрерывный накопитель phase state-summary'ев (founder-директива 2026-07-09; `run.md` exit-ritual §6e).
> Каждая завершённая фаза **prepend**'ит сюда свою справку (2 блока: техническое состояние + пользовательские
> сценарии; формат — [`_meta/state-summary-template.md`](./_meta/state-summary-template.md)). Полные картины
> волн — в `roadmap/<wave>/WAVE-N-SUMMARY.md`. Свежее — сверху.

---

## Текущий срез: Wave 1 (Core MVP) — must-set код-полно, задеплоено+verified на VPS

Полная справка волны → [`roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md`](./roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md).
Формальное закрытие — за founder (обзор вертикалей draft→reviewed, cost/risk review, подпись гейта).

---

## Phase deltas (свежее сверху)

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
