# READY-TO-BUILD STATUS — 2026-05-12

> Финальный документ после полного SYNTHESIS-цикла + точечного грилла. Проектная документация переведена в **ready-to-build** состояние для AI-агентов разработки.

## Что сделано (consolidated change-list)

### ADR (22 шт. в каталоге)

**8 existing ADR обновлены** под SYNTHESIS-решения Q1-Q12:
- ADR-001: Vite+React+TanStack frontend (вместо Next.js)
- ADR-002: Триконтурный LLM-стек + BYOK first-class (DeepSeek + RU + Western Wave 2+)
- ADR-004: Native Canvas 2D + AI-generated + 5 vertical-героев (вместо PixiJS)
- ADR-006: Pyodide WASM в Wave 2 (вместо gVisor)
- ADR-007: Custom JWT в Wave 0-1 (вместо Authentik), Logto Wave 2-3
- ADR-008: Pricing — Solo ₽990 + Команда 5/15/30 ₽1900/4900/9900 + BYOK режим
- ADR-009: Cell-as-first-class-concept с дня 1 (логические cells на shared physical)
- ADR-011: Persistent memory в Wave 2, «Знания команды» (PARA) Wave 3
- ADR-013: MCP-протокол с Wave 0 (вместо Composio)

**7 новых ADR созданы:**
- ADR-016: Team-first UX (нанять команду одним кликом)
- ADR-017: 5 vertical-templates (WB + Маркетинг + Telegram + Бухгалтерия + Sales)
- ADR-018: DeepSeek как primary LLM (V3 + R1)
- ADR-019: Vertical-specific Autonomous Mode + «Знания команды»
- ADR-020: Pyodide WASM в браузере для Analyst
- ADR-021: AI-generated pixel + 5 hand-drawn vertical-героев
- ADR-022: Coordinator wizard + LLM hybrid

### Reference-файлы (5 шт.)

- **PROJECT.md** — entry-point с обновлённой navigation, статусом, ADR-индексом
- **_meta/stack.md** — полный технический стек (Vite, DeepSeek, MCP, Pyodide, Custom JWT, Yandex Cloud)
- **_meta/glossary.md** — добавлены Cell / Vertical-template / Rituals / BYOK / Знания команды / MCP-сервер / Pyodide
- **_meta/open-questions.md** — 12 OQ закрыты, 13 open (нет blockers для архитектуры)
- **decisions/README.md** — обновлённый ADR-каталог (22 шт.)

### Risks-register

- **30 рисков** (R-01...R-30) с mitigation, owner, monitoring
- **R-13, R-15 — closed** (Composio dependency сняты)
- **R-29 — closed** (in-house domain expertise)
- **R-09 — mitigated** (PixiJS-bottleneck снят через Canvas)
- **R-14 — mitigated** (Pixel-art bottleneck снижен через AI-pipeline)
- Стратегические ставки с kill criteria (5 vertical-templates + DeepSeek + MCP + Pixel + Autonomy)

## Решения, зафиксированные в SYNTHESIS + точечном грилле

### SYNTHESIS Q1-Q12 (2026-05-12)

| # | Решение |
|---|---|
| Q1 | Team-first UX в MVP, role-swap в Wave 3+ |
| Q2 | РФ-вертикальная экспертиза как primary USP |
| Q3 | Логические cells с дня 1 |
| Q4 | DeepSeek + YandexGPT + GigaChat в Wave 0, BYOK для 3 провайдеров |
| Q5 | MCP-протокол + кураторский каталог (Composio не используем) |
| Q6 | Vertical-specific autonomy + core Wave 2 + PARA Wave 3 |
| Q7 | Vite + React 19 + TanStack Router + FastAPI отдельно |
| Q8 | Custom JWT Wave 0-1, Logto Wave 2-3, Keycloak только Enterprise |
| Q9 | AI-generated baseline + 5 vertical-героев hand-drawn + РФ-стилистика |
| Q10 | Wizard для onboarding + LLM-Coordinator для trial/paid с credit-limit |
| Q11 | Pyodide для аналитики Wave 2, gVisor только при необходимости Wave 3+ |
| Q12 | 5 templates: WB-Селлер + Маркетинг + Telegram + ИП-Бухгалтерия + СМБ-Sales |

### Точечный грилл (2026-05-12)

| # | Решение |
|---|---|
| Pricing | Solo ₽990 + Команда 5/15/30 ₽1900/4900/9900 + BYOK режим (-50% от managed) |
| Infrastructure | Monorepo + GitHub primary + GitLab mirror + GitHub Issues + Yandex Tracker + Yandex Cloud ru-central-1 |
| R-29 | Snят (in-house domain expertise) |
| Stack default | «Оптимальное качество» + UI-prompt при cell creation (без упоминания China/конкретных моделей) |
| Email | Yandex 360 SMTP (Wave 0-1) → UniSender/Notisend (Wave 2+) |

## Состояние всех файлов `.planning/`

```
.planning/
├── PROJECT.md                                ✅ обновлён
├── SYNTHESIS-2026-05-12.md                   ✅ создан (change-list)
├── READY-TO-BUILD-2026-05-12.md              ✅ этот файл
│
├── _meta/
│   ├── stack.md                              ✅ полностью переработан
│   ├── glossary.md                           ✅ обновлён с новыми терминами
│   ├── conventions.md                        ⚪ без изменений (стабильный)
│   ├── agent-protocol.md                     ⚪ без изменений
│   └── open-questions.md                     ✅ 12 закрыто, 13 open
│
├── decisions/
│   ├── README.md                             ✅ обновлённый ADR-каталог (22 шт)
│   ├── ADR-template.md                       ⚪ без изменений
│   ├── ADR-001-modular-monolith.md           ✅ revised (Vite+React)
│   ├── ADR-002-llm-gateway.md                ✅ revised (триконтурный + BYOK)
│   ├── ADR-003-pydantic-ai-runtime.md        ⚪ без изменений
│   ├── ADR-004-pixel-department.md           ✅ revised (Canvas + AI-pipeline)
│   ├── ADR-005-pgvector-then-qdrant.md       ⚪ без изменений
│   ├── ADR-006-gvisor-then-firecracker.md    ✅ revised (Pyodide MVP)
│   ├── ADR-007-authentik-then-keycloak.md    ✅ revised (Custom JWT MVP)
│   ├── ADR-008-credits-billing.md            ✅ revised (Solo + новые цены + BYOK)
│   ├── ADR-009-multitenancy-3-levels.md      ✅ revised (Cell с дня 1)
│   ├── ADR-010-role-versioning.md            ⚪ без изменений
│   ├── ADR-011-memory-2-level.md             ✅ revised (persistent W2 + PARA W3)
│   ├── ADR-012-artifacts.md                  ⚪ без изменений
│   ├── ADR-013-mcp-protocol.md               ✅ revised (W0 first-class)
│   ├── ADR-014-security.md                   ⚪ без изменений
│   ├── ADR-015-ai-dev-process.md             ⚪ без изменений
│   ├── ADR-016-team-first-ux.md              ✅ new
│   ├── ADR-017-vertical-templates.md         ✅ new (5 templates)
│   ├── ADR-018-deepseek-primary-llm.md       ✅ new
│   ├── ADR-019-vertical-autonomous-mode.md   ✅ new
│   ├── ADR-020-pyodide-code-execution.md     ✅ new
│   ├── ADR-021-ai-generated-pixel-pipeline.md ✅ new
│   └── ADR-022-coordinator-wizard-llm-hybrid.md ✅ new
│
├── risks/
│   └── REGISTER.md                           ✅ полностью обновлён (R-01...R-30)
│
├── roadmap/
│   ├── wave-0-foundation/                    ⚠️ phase-файлы требуют sync (см. ниже)
│   ├── wave-1-core-mvp/                      ⚠️ phase-файлы требуют sync
│   ├── wave-2-pixel-catalog/                 ⚠️ phase-файлы требуют sync
│   ├── wave-3-depth/                         ⚪ структура OK, мелкие правки
│   ├── wave-4-scale-partner/                 ⚪ структура OK
│   └── wave-5-enterprise/                    ⚪ структура OK
│
└── research/
    └── teamly_to_analysis/                   ⚪ исторический документ (закрыто)
```

## Что ещё требует синхронизации (НЕ блокирует старт Wave 0)

**Phase-файлы Wave 0-2** написаны под прежнюю архитектуру (Next.js / Authentik / Anthropic / gVisor). Их нужно переписать под новые ADR. Это можно сделать **в первый день Phase 00.1**:

| Phase | Изменения |
|---|---|
| Phase 00.1 (repo+CI) | Monorepo structure, GitHub + GitLab mirror, Yandex Tracker integration, Vite scaffold |
| Phase 00.2 (auth) | Custom JWT вместо Authentik, Yandex 360 SMTP, РКН-уведомление prerequisite |
| Phase 00.3 (DB+RLS) | Cell-aware schemas, multi-tenant pattern |
| Phase 00.4 (LLM-gateway) | DeepSeek + YandexGPT + GigaChat + BYOK + MCP infra |
| Phase 00.5 (runtime) | WB-Селлер team-preset (вместо Writer-only) |
| Phase 00.6 (deploy) | Без существенных изменений |
| Wave 1 phases | 3 vertical-templates, persistent memory, billing с Solo, Coordinator wizard |
| Wave 2 phases | 5 vertical-templates, Pixel Department (Canvas+AI), Pyodide, MCP-каталог |

**Рекомендация:** AI-агенты разработки получат текущие ADR + SYNTHESIS + open-questions, и **сгенерируют свежие phase-файлы** на основе обновлённой архитектуры в Phase 00.1 (это лучше, чем patching старых phase-файлов вручную).

## Готовность к Wave 0 (чек-лист)

| Категория | Статус |
|---|---|
| ADR-каталог (22 ADR) | ✅ READY |
| Reference-файлы | ✅ READY |
| Risks-register (30 рисков) | ✅ READY |
| Stack-документ | ✅ READY |
| Glossary | ✅ READY |
| Phase-файлы Wave 0-2 | ⚠️ Требуют sync (выполняется в Phase 00.1) |
| Open Questions критичные для Wave 0 | ⚠️ 5 OQ требуют founder-decision (юр.форма, hire, funding, РКН) |
| Customer-validation (R-29) | ✅ Снято (in-house expertise) |

## Action items для founder'а (до Phase 00.1)

**Срочные (this week):**
1. Решить **OQ-02** (ООО vs ИП) → или отложить и стартовать pre-Wave-0 без юр.лица для ранних работ
2. Решить **OQ-13, OQ-14** (Tech Lead + Senior Backend hire) — startup-критично
3. Решить **OQ-17, OQ-18** (funding/burn budget)
4. **OQ-04** — подать уведомление РКН об операторе ПДн (2 часа, до Phase 00.2)

**К Wave 0 start:**
5. Open ЮKassa account (5-10 дней процедура) — нужно до Wave 1.4 (billing)
6. Зарегистрировать GitHub Organization
7. Создать Yandex Cloud cloud-account + первый проект `teamly-ru-dev`

**Параллельно (не блокирует разработку):**
8. Domain + brand TBD (OQ-09) — нужен к Wave 2
9. Регистрация товарного знака — нужен к Wave 2 publication

## Action items для команды (Phase 00.1, day 1)

1. **Tech Lead:** Прочитать SYNTHESIS + все ADR + risks-register (4-6 часов первый раз)
2. **Senior Backend:** PoC DeepSeek + YandexGPT + GigaChat SDK через единый интерфейс (~1 день)
3. **Senior Frontend (когда найден):** PoC Vite + TanStack Router skeleton + Pyodide-in-browser test (~1 день)
4. **DevOps:** GitHub repo + GitLab mirror setup + Yandex Cloud Terraform + Docker Compose dev-environment
5. **AI-agents разработки:** перечитать `_meta/agent-protocol.md` + старт работы по pa-фазам

## Метрики готовности

**До SYNTHESIS:**
- Wave 0 time: 4 нед / Wave 0-1 total: 10 нед
- Pixel-art бюджет: $25K+
- Sandbox-инфра Wave 2: $50-100/mo + 8 дней
- Backend services Docker Compose: 4 (PostgreSQL + Redis + Authentik + Backend)

**После SYNTHESIS:**
- Wave 0 time: **3 нед** (-25%) / Wave 0-1 total: **9 нед** (-10%)
- Pixel-art бюджет: **$3-5K** (-80%)
- Sandbox-инфра Wave 2: **$0** (Pyodide) + 3 дня
- Backend services Docker Compose: **3** (PostgreSQL + Redis + Backend) — без Authentik
- Wave 0 — БЕЗ VPN, БЕЗ зарубежного юр.лица, БЕЗ прокси-посредников

## Финальный statement

🎯 **Проект ready для AI-agent-driven development.** Любой AI-агент разработки, получив текущий `.planning/` directory как context, может:

1. Прочитать PROJECT.md → ориентация (1 раз)
2. Прочитать SYNTHESIS + READY-TO-BUILD → текущий статус (1 раз)
3. Прочитать конкретный phase-spec → начать работу
4. Ссылаться на ADR / glossary / stack по необходимости

**Целевая дата начала Wave 0:** **2026-05-19** (через 1 неделю с момента synthesis) при условии быстрого решения 5 founder-OQ.

---

**Documentation status: READY-TO-BUILD ✅**

Готов передать AI-agent-команде для составления финального пошагового плана работы.
