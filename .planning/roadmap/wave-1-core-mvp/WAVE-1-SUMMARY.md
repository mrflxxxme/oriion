# Wave 1 (Core MVP) — итоговая справка о состоянии

> Wave state-summary per методология (`run.md` stop-conditions / [state-summary-template](../../_meta/state-summary-template.md)).
> Составлена `/autonomy:run` 2026-07-09 по факту merge всех must-фаз. Формальное закрытие волны — за founder (см. §3).

## Резюме
Wave-1 must-множество (**01.9a+01.9b + 01.4-ui + 01.10 + 01.12**) — **код-полно, смержено в `main` (`ce83ed2`), задеплоено и проверено на VPS** `staging.профики.online`. Автономно-вычислимые пороги wave-гейта пройдены; формальное закрытие требует подписи founder (обзор вертикалей draft→reviewed, cost/risk review).

## 1. Техническое состояние волны

### Архитектура (bounded contexts)
`iam` (auth/JWT/2FA/magic-link/sessions) · `multitenancy` (workspace/cell + RLS) · `billing` (Trial + caps) · `agents` (Master-Agent 2-level + archetypes + verticals + team-provisioning) · `runtime` (Dramatiq worker + orchestrator + dispatch + tool-gating) · `llm_gateway` (DeepSeek/Yandex/GigaChat + BYOK + KMS) · `memory` (2-level + Yandex embeddings) · `artifacts` (Yjs + S3 + citeable URLs) · `security` (DLP + injection + capability) · `mcp` (connectors + creds) · `audit`. Frontend: Vite/React/TanStack/shadcn, tokens v0.2.

### Что построено в этой волне (must-set)
- **01.9a — DLP-активация:** context-aware INN-детектор (FP 11%→**0%**, golden-корпус 720 строк), оба security-флага (`security_dlp_enabled` + injection) **ON в проде**. Закрыты DV-04/DV-05. SECURE-аудит PASS.
- **01.9b — коннекторы (read+draft):** 3 native-tool коннектора (telegram-bot Bot-API / yandex-disk / imap-smtp), capability-gate активирован (DANGEROUS-send denied до approval-UI), KMS creds-store (`mcp.connector_credentials`, workspace-RLS), DLP-скрин исходящих аргументов. ADR-041. SECURE-аудит PASS.
- **01.4-ui — панель памяти:** просмотр/поиск/добавление/удаление cell- и role-memory.
- **01.10 — 2-я вертикаль `telegram_creator`:** research-first (17 источников) + Master/role draft-промпты + 30-task golden + 5 adversarial; live-golden **7/7** (~$0.03).
- **01.12 — Dashboard + Onboarding:** 3-шаговый онбординг-визард + Dashboard-сводка; team-provisioning маршрутизирует все 3 пресета.

### Качество
Все фазы: ruff + mypy --strict (241 файл) + bandit 0 + unit **1136+** + per-module coverage ≥85% + real-PG integration зелёные в CI. Evidence: adversarial-audit (01.9a/01.9b) + live-golden (01.10). D7-heal: 1 регрессия (test-isolation + coverage 01.9b) — forward-fix за 2 цикла, main здоров.

### Deploy (VPS, verified 2026-07-09)
`main` задеплоен, миграция `mcp_0002_connector_credentials` применена. Проверено на сервере: DLP-флаги ON; capability-gate режет `send_telegram`, пускает `telegram_read`; таблица connector_credentials живёт; маршруты `/memory`, `/dashboard`, `/onboarding` отдают 200; healthz ok.

### Долг / открытые риски
Open DV (не-P1): DV-11 (connector live-smoke — нужны креды), DV-12/DV-02 (вертикали draft→reviewed — founder-review), DV-06 (SMTP live). Deferred-security (до включения autonomous send, ≥Wave-2): fail-open scoping→fail-closed, layer-B PII→layer-A ML. Parked: 01.3b/01.8b/01.11 (RUNWAY). Post-wave dev-infra: 01.8c.

## 2. Реализованные пользовательские сценарии (end-to-end)
1. **Регистрация → первая ценность без инструкций:** пользователь регистрируется → авто-создаётся trial-ячейка + грант Trial 14д/500 → онбординг-визард (выбор пресета из 3) → первая задача → результат-артефакт на Dashboard. *(01.12 + 01.3; e2e-спека @live готова, server-routes verified)*
2. **Мультиагентная задача (горизонталь):** «Маркет-бриф» → 3-агентная команда → SSE-прогресс → markdown-артефакты. *(live-proven ранее)*
3. **Вертикаль «Маркетинг-агентство»** и **«Telegram-крейтор»:** доменный Master-Agent даёт план+синтез с учётом РФ-специфики (ФЗ-38, РКН-реестр, 152-ФЗ). *(01.10 live-golden 7/7; промпты draft — до founder-review)*
4. **Память команды:** пользователь видит/ищет/добавляет/удаляет, что помнит команда/агент. *(01.4-ui, server-verified)*
5. **Артефакты:** результаты как версионируемые артефакты (Yjs/S3) с citeable `artifact://` ссылками. *(01.5)*
6. **Биллинг/защита:** Trial-гранты, cost-caps (soft-warn→hard-block), DLP не выпускает РФ-ПДн в выводе. *(01.3 + 01.9a, DLP verified ON на проде)*
7. **Коннекторы (substrate):** агент может read+draft из Telegram/Диск/IMAP; автономная отправка запрещена до approval-UI. *(01.9b — построено+mock; live-round-trip = DV-11, нужны креды)*

## 3. Что нужно от founder для формального закрытия волны
- **Обзор вертикалей draft→reviewed** (telegram_creator + agency_marketing_ru) — подпись REVIEW-CHECKLIST → закрывает DV-12/DV-02 + порог «2nd vertical reviewed».
- **Креды (отдельно):** RW-03 Telegram bot-token, RW-01 SMTP/IMAP, Yandex Disk OAuth → закрывает DV-11 + live Bot-API демо + DV-06 SMTP live-send.
- **Cost-budget review** (v4 50/75) + **risks review** + **founder_signature** на `gates/wave-1-to-2.md`.
- (Опционально) RW-07 staging anchor-run — формально закрывает Wave 0.

## 4. Метрики / бюджет
Смержено 11 PR (#94–#104). Live-LLM спенд волны ≈ **$0.03** (01.10 golden; остальное — детерминированные проверки, server-verify без live-run). Dev-team (Claude-agent) спенд сессии ≈ $25–40 (в рамках hard $75 v4). Founder-touchpoints: несколько self-ack (авторизованы «продолжай до конца волны») + этот обзор. Heal: 1 (2 цикла).
