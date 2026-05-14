# ADR-026: Vertical-expertise pipeline — D-pattern + anti-hallucination protocol

- **Status:** Accepted

## Decision

Покрывает [GRILL-DECISIONS-ORIION](../decisions/ADR-028-policies-registry.md) DECISION-6 (vertical-expertise модель) + DECISION-11 (anti-hallucination protocol). Фиксирует, как создаётся, проверяется и поддерживается контент для каждой из 5 vertical-templates ([ADR-017](./ADR-017-vertical-templates.md)).

### 1. Pattern D — AI-baseline + founder edit + friends-loop

Pipeline для нового vertical-template:

```
1. vertical-prompt-author (AI, Sonnet или Opus)
   → черновик coordinator.md + researcher.md + остальные роли (AI baseline)
2. Founder edit
   → правки на основе personal operating expertise
3. evaluator (LLM-as-judge, AgentDB-backed)
   → golden-dataset run + adversarial probes
4. Wave 1+ only: ICP-friends-loop validation
   → 3-5 friends per vertical × 5 реальных задач каждая → ≥80% ✅
5. status: locked → промпт становится production-ready
```

**Founder = real-world expert** по всем 5 vertical-templates (WB-Селлер, Marketing-Агентство, TG-Крейтор, ИП-Бухгалтерия, SMB-Sales), что закрывает [R-29](../risks/REGISTER.md#r-29-founder-vertical-expertise-gap). Vertical content validation gate — не «AI claim», а personal operating expertise + structured re-verification.

### 2. `verticals/<slug>/` structure

```
.planning/verticals/<vertical-slug>/
├── README.md              # ICP, JTBD, KPI, primary tasks
├── domain-glossary.md     # термины (FBO, FBS, артикул, выкуп, рейтинг, ...)
├── workflow-dag.md        # как агенты взаимодействуют (Coordinator → Researcher → Writer → ...)
├── prompts/
│   ├── coordinator.md     # полный system-prompt (versioned, см. ADR-010)
│   ├── researcher.md
│   └── <role>.md
├── golden-dataset/
│   ├── README.md          # методология (LLM-as-judge criteria + rubrics)
│   └── tasks/
│       ├── 001-<slug>.md  # task: input + expected-output-shape + rubric per task
│       └── ...            # 30 tasks per vertical (10 easy / 15 medium / 5 hard)
├── REVIEW-CHECKLIST.md    # founder-review checklist
├── kpis.md                # business-метрики (TTFV, success-rate, NPS)
└── changelog.md           # изменения промптов (regression-tracking)
```

Wave 0 deliverable: `verticals/wb-seller/` полностью готов (~40-60 файлов) — единственная вертикаль на Phase 00.5. Wave 1+ — остальные четыре. Конкретная генерация — Milestone B (skeleton) + Phase 00.5 (наполнение для WB-Селлер).

### 3. Wave 0 anti-hallucination — Level B (founder=expert + evaluator gate)

Применяется ко всем prompt-файлам в WB-Селлер до прохождения gate Wave 0 → Wave 1:

- **Source-citation** требуется в каждом factual claim промпта. URL + accessed-date в frontmatter (см. §5).
- **Founder-review checklist** обязателен перед `status: reviewed`. Lives in `REVIEW-CHECKLIST.md` per vertical.
- **Evaluator gate:**
  - 30 golden-dataset tasks → ≥75% pass-rate под LLM-as-judge rubric.
  - 5 adversarial probes (промпт-инъекции, граничные кейсы, противоречивые инструкции) → **100%** pass (любой fail блокирует promote).
- **90-day re-verification cycle** — memory-curator triggers PR при `next-verification` < today + 7d. PR содержит rerun evaluator + diff к источникам.

### 4. Wave 1+ anti-hallucination — Level C (friend-loop)

Дополнительно к Level B:

- **3-5 ICP-friends** per вертикаль. Each runs 5 реальных задач из своей операционной практики.
- **≥80% ✅ rating** → `status: locked`. Меньше — обратно в draft, founder editing loop.
- **Negative examples** → новые golden-dataset tasks (rolling expansion). Failed task становится regression-fixture.
- **Comparison oracle** (с Wave 2): один и тот же task запускается на DeepSeek vs YandexGPT vs GigaChat → divergence-flag, если ответы расходятся семантически. Высвечивает hallucinations + provider-specific bias.

### 5. Frontmatter contract для `prompts/<role>.md`

```yaml
---
role: coordinator
vertical: wb-seller
version: 0.1.0                       # SemVer per ADR-010
status: draft | reviewed | promoted | locked
verified-by: [founder-review, evaluator-pass]
verified-at: 2026-05-20
verified-sources:
  - url: https://seller.wildberries.ru/...
    accessed: 2026-05-12
    relevance: Описание FBO/FBS схемы
  - url: ...
golden-dataset-pass-rate: 0.83
adversarial-probes-pass-rate: 1.0
hallucination-flags: []              # known issues, не блокирующие
friend-validation:
  participants: 0                    # 0 на Wave 0
  positive-rate: null
  comments: []
next-verification: 2026-08-13        # +90 days
---
```

Изменение значимых полей (`version`, `status`, `verified-sources`) → PR с reviewer-backend + founder approval. Изменение `version` следует SemVer policy из ADR-010 (revised).

### 6. 90-day re-verification cycle

memory-curator (см. ADR-023) ежедневно сканирует все `verticals/<slug>/prompts/<role>.md`:
- Если `next-verification - today < 7 days` → создать PR с заголовком `chore(vertical): re-verify <vertical>/<role>`.
- PR прикрепляет: actual evaluator rerun results, diff'ы к `verified-sources` URLs, suggested updates.
- Founder review → либо approve (bump `next-verification` на 90 дней), либо revise (back to draft).

## Consequences

- **R-29 closes:** founder vertical-expertise reality — не gap, а foundation. [R-29](../risks/REGISTER.md#r-29-founder-vertical-expertise-gap) переводится в `closed (resolved)`.
- **Wave 0 single-vertical focus:** только WB-Селлер. Остальные четыре vertical-templates — Wave 1+ delivery. Это сужает Wave 0 scope в Phase 00.5 до one-vertical-only.
- **Versioning prompt-файлов** — через SemVer per [ADR-010](./ADR-010-role-versioning.md) (revised — scope clarification, что versioning применяется к prompt-файлам, не к archetype assets).
- **Rolling regression-fixtures:** golden-dataset растёт со временем за счёт failed friend-tasks. Это уменьшает hallucination surface monotonically.
- **Auditable verification:** каждая claim в промпте имеет cited source с accessed-date. Через 6 месяцев founder может пройти аудит почему prompt написан так.
- **evaluator роль** (см. ADR-023) — постоянный quality gate. Без `evaluator-pass` в `verified-by` — `status: locked` недостижим.

## Links

- [GRILL-DECISIONS-ORIION](../decisions/ADR-028-policies-registry.md) — DECISION-6, DECISION-11
- [ADR-010](./ADR-010-role-versioning.md) — SemVer policy для prompt-файлов (revised — scope clarification)
- [ADR-017](./ADR-017-vertical-templates.md) — 5 vertical-templates как primary USP
- [ADR-023](./ADR-023-ai-team-runtime.md) — evaluator + vertical-prompt-author + memory-curator
- Risk: [R-29](../risks/REGISTER.md) — closed (resolved) via founder personal operating expertise
- Strategic bets + kill criteria: [risks/REGISTER.md](../risks/REGISTER.md#стратегические-ставки-с-kill-criteria)
