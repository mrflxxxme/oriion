# ADR-039: Security guardrails — bounded context + deterministic detector ports

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** Founder (grill 2026-07-03, pre-resolved — см. [DECISIONS-LOG](../_session-context/DECISIONS-LOG.md) 2026-07-03T14:09/14:20/14:33) + runner (ADR-037 D4)

## Context

[ADR-014](./ADR-014-security.md) §2/§3 задаёт многослойную защиту: input/output
фильтрацию (prompt-injection на входе, DLP-классификатор ПДн на выходе) +
capability sandboxing («опасные» tools требуют human approval). Phase **01.6**
помечена в [PHASES.md](../roadmap/wave-1-core-mvp/PHASES.md) как **блокирующий
гейт «до любого PII-surface»** — она должна существовать раньше, чем появится
первый исходящий канал ПДн (connectors 01.9, Telegram Business 01.11).

Силы, давящие на решение (грил 2026-07-03):

1. **Гейт не должен нести stuck-risk.** Блокирующая фаза не может зависеть от
   model-serving / funded-download (ML-инференс Prompt Guard / bge) или live-LLM
   (LLM-as-judge) — иначе отсутствие Docker/funded-`.env` замораживает весь
   pipeline. RU-ПДн (ИНН/СНИЛС/паспорт) **детерминированно ловится по checksum'у**
   — сильная сторона regex + объяснимость для security review.
2. **Wave-1 injection-риск низкий.** Внешний контент = только `web_search` /
   `read_url` (read-only); исходящих action-tools нет до 01.9. Значит тяжёлый
   ML-детектор инъекций сейчас не окупается.
3. **Апгрейд-путь нельзя закрывать.** Wave-2+ захочет ML-модели (Prompt Guard,
   bge) без переписывания call-site'ов.
4. **Нет surface — нет enforcement.** Соседние решения этой же фазы (capability
   gate → 01.9; storage-квоты → Wave-2; co-editing → Wave-2) следуют паттерну
   **«substrate/seam сейчас, enforcement когда появится что защищать»**. Guardrails
   держат тот же паттерн.

## Decision

Новый bounded context **`security`** с **detector-портами** и Wave-1
имплементацией на **детерминированном слое B** (regex + checksum-валидация); порт-шов
позволяет заменить B→A (Prompt Guard / bge ML) позже без изменения call-site'ов.

### 1. Bounded context `backend/src/security/`

Зеркалит layout `src/memory` / `src/artifacts`, но **без собственных таблиц и
миграций** — детекторы stateless, а DLP-блок пишет строку в **существующую**
`audit.audit_log` через `audit.services.emit_audit_event(session=…)`. Нулевой
migration-footprint = нулевой `db_migrations`-tripwire = гейт остаётся
детерминированным и Docker-независимым.

### 2. Детекторы = порты + детерминированные адаптеры (слой B)

- **DLP (RU-ПДн):** `PiiDetector`-порт; Wave-1 адаптер — regex + checksum:
  ИНН-10/ИНН-12 (контрольные разряды), СНИЛС (контрольная сумма mod 101),
  паспорт РФ (серия+номер), телефон РФ, e-mail. Каждая находка = `(category,
  span)` — **никогда сырое значение в логах/аудите** (зеркало logging-контракта
  memory-extraction).
- **Injection:** `InjectionScanner`-порт; Wave-1 адаптер — эвристики + известные
  паттерны (instruction-override, role-switch, system-prompt-exfil).
- **Port seam:** апгрейд B→A (ML) = новая реализация порта, call-site не меняется.

### 3. Триггеры (грил 2026-07-03)

- **Output DLP = A3** — hard-block: строка в `audit.audit_log` + явная ошибка
  задачи (`security.dlp.blocked`), **без** интерактивного approval (approval-UI =
  01.12, ложится на тот же шов позже). Масштабирование `str(exc)` в SSE →
  `DlpViolation` несёт **только категории, не сырое ПДн**.
- **Input injection = B1** — strip/neutralize помеченного фрагмента + продолжить
  с пометкой (не блокировать весь легитимный контент из-за одной инъекции).

### 4. Enforcement-состояние в Wave-1 (substrate-now, enforce-at-surface)

Поведение A3/B1 **полностью реализовано + протестировано**, активация — через
флаги в `Settings`. **Оба флага default OFF в Wave-1** (substrate + seam готовы;
enforcement включается на первом исходящем surface — 01.9 — вместе с
owner-config; идентично capability-gate решению этой же фазы):

- `security_dlp_enabled` = **False**: A3 hard-block несёт false-positive-friction
  (легитимный маркетинг-бриф с телефоном/номером клиента), а **исходящего
  PII-surface в Wave-1 нет** (артефакты cell-scoped под RLS; connectors = 01.9).
- `security_injection_scan_enabled` = **False** (пересмотрено adversarial-аудитом
  2026-07-03): исходно default-ON под тезисом «B1 недеструктивна / no-op на
  benign». Аудит опроверг тезис — эвристики калечат легитимный веб-контент,
  который *цитирует* атаку или содержит LLM-template-маркеры. Внешнего
  unattended-коннектора в Wave-1 нет (web read-only, low-risk), поэтому дефолт
  ушёл в OFF (паттерны ужесточены: убраны голые `developer mode`/`jailbreak` и
  markdown-заголовки). Включается в 01.9 вместе с DLP.

Гейт **построен** (требование «до любого PII-surface» = существовать раньше 01.9),
активация = флаг-флип + owner-config.

### 5. Capability sandboxing = классификатор + seam, без gate

`tools_allowed` живёт на `agents.agent_archetypes` (НЕ `agents.roles` — этой
таблицы нет; и `risk_level`-колонки нет). Риск инструмента — **детерминированный
статический реестр** `TOOL_RISK` в контексте (нет миграции), + `classify_tool()`
/ `requires_approval()` (fail-closed: unknown → dangerous). **Реального
capability-gate в 01.6 нет** — активируется в 01.9, когда приземлятся первые
исходящие connectors + owner-config surface (грил 2026-07-03T14:33).

### 6. Runtime-швы (зеркало `quota_admission` / `memory_extraction`)

- Output DLP: `OutputDlpScreen`-шов на `execute_agent_task` (default `None` ⇒
  no-op в unit-тестах; worker `runtime.queue.actor` подключает реальный,
  собранный `runtime.security_guardrails.build_output_dlp_screen`, gated флагом).
  Скрин на `_dlp_screen_text(output)` — **полная** outward-сериализация
  (`json.dumps(model_dump())`, без cap), чтобы `screened ⊇ delivered` (НЕ
  усечённый memory-filter `_deliverable_text` — иначе ПДн за cap'ом проходит мимо
  блока; аудит 2026-07-03). Вызов **до** memory-extraction и success-stamp; любой
  raise из скрина → `task.failed` + actor коммитит audit-строку.
- Input injection: sanitize на `runtime.web_search_runner._format_search_results`
  (единый chokepoint scripted+native путей), gated флагом.

## Consequences

- ✅ **Детерминированный, Docker-независимый блокирующий гейт** — unit-тестируем
  целиком, без funded-ключей и model-serving (прямое исполнение «no stuck-risk»).
- ✅ **Explainable для security review** — checksum-валидация ИНН/СНИЛС = zero
  ML-чёрный-ящик; каждая находка объяснима.
- ✅ **Апгрейд-путь открыт** — B→A (ML) = порт-swap, нулевое изменение call-site.
- ✅ **Нулевой tripwire** — нет миграций, контрактов, auth/billing/secrets путей →
  auto-merge на зелёном (низкофрикционная блокирующая фаза).
- ⚠️ **Слой B ловит форматно-регулярное** — checksum-ПДн + известные
  injection-паттерны; свободный неструктурированный ПДн / новые
  injection-техники ждут ML (A). Приемлемо для Wave-1 (внутренний pre-alpha,
  RU-ПДн формат-строгий).
- ⚠️ **DLP default-off** — реальная защита исходящего ПДн включается в 01.9. До
  тех пор — substrate + audit-substrate, не активный блок (по построению: нет
  surface).
- 🔮 **Future:** 01.9 флипает `security_dlp_enabled` + активирует capability-gate;
  01.12 добавляет approval-UI на тот же шов; Wave-2+ ставит ML-порт (A).

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| **ML-детекторы сейчас (A)** — Prompt Guard / bge | Ловит свободный ПДн + новые инъекции | Model-serving / funded-download = stuck-risk на блокирующем гейте | Против «no stuck-risk»; RU-ПДн детерминирован |
| **LLM-as-judge DLP** | Гибкий, контекстный | Per-call cost/latency + funded-key на near-absent pre-alpha сценарии | Дорого + зависимость от ключей на гейте |
| **DLP-таблица `security_events`** | Отдельный audit-стрим | Новая миграция = `db_migrations`-tripwire + Docker-зависимый тест | `audit.audit_log` уже есть, append-only, RLS-scoped |
| **`risk_level`-колонка на archetypes** | «данные, не код» | Миграция + колонки нет + capability gate не нужен в 01.6 | Статический реестр = нет миграции, тот же результат |
| **DLP default-on hard-block** | «настоящий» блок сразу | False-positive friction на cell-internal deliverables без исходящего surface | Нет surface = friction без выгоды; включаем в 01.9 |
| **Interactive approval (A1) на DLP** | Мягче hard-block | Невозможно без UI (01.12); блокирующий гейт не может ждать далёкую UI-фазу | A3 честный стоп, шов примет approval позже |

## Links

- Реализует: [ADR-014](./ADR-014-security.md) §2 (input/output фильтрация) + §3 (capability sandboxing, seam-часть)
- Использует шов-паттерн: [ADR-011](./ADR-011-memory-2-level.md) memory-extraction seam + billing quota_admission seam
- Runner: [ADR-037](./ADR-037-autonomous-multiphase-runner.md) D4 (owned fork) — грил 2026-07-03 pre-resolved
- Risks: [R-02](../risks/REGISTER.md) (prompt injection), [R-05](../risks/REGISTER.md) (data leak)
- Phase: [01.6-security-guardrails](../roadmap/wave-1-core-mvp/phases/01.6-security-guardrails.md)
- Cross-ref активации: 01.9 (capability gate + DLP flip + owner-config), 01.12 (approval-UI)
