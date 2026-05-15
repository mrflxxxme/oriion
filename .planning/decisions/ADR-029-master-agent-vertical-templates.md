# ADR-029: Master-Agent layer для vertical-templates

- **Status:** Proposed
- **Date:** 2026-05-15
- **Deciders:** Founder, Tech Lead (architect AI-role)
- **Supersedes:** N/A
- **Superseded by:** N/A

## Context

После Session-decision (2026-05-15) о реорганизации roadmap-а:

1. Wave 0 теперь шипит **horizontal team-preset** `productivity-core` («Твои личные ассистенты») — Coordinator + Researcher + Writer + Analyst. Цель — universal entry-point с уклоном в продуктивность / аналитику / маркетинг.
2. Wave 1+ vertical-templates (Marketing-agency, Telegram-крейтор, WB-Селлер, ИП-Бухгалтерия, СМБ-Sales) шипятся поверх валидированной horizontal-команды.
3. Vertical-templates обладают глубокой ниша-экспертизой, специфичными rituals, доменными compliance-требованиями. Эта экспертиза должна жить **в роли**, а не размазываться по prompt-ам всех specialists.

Существующая [ADR-022](./ADR-022-coordinator-wizard-llm-hybrid.md) определяет Coordinator-а как top-level orchestrator. Для horizontal preset-а этого достаточно — domain-knowledge не требуется. Для verticals требуется отдельный role-layer, который:

- хранит ниша-экспертизу (терминология, workflow, regulatory context, KPI бизнеса в нише),
- задаёт vertical-specific workflow (priority decisions, escalation gates, rituals),
- выступает «CEO» команды агентов, делегируя operational orchestration существующему Coordinator-у.

## Decision

Вводим **двухслойную оркестрацию для vertical-templates** (Wave 1+):

```
Vertical template (Wave 1+):
  Master-Agent (vertical CEO) — domain knowledge + workflow
    └── Coordinator (operational COO) — task decomposition + agent assignment (re-used из ADR-022)
        ├── Researcher
        ├── Writer
        ├── Analyst
        └── + vertical-specific specialists (Listing Writer for WB, Accountant for ИП, и т.д.)
```

**Horizontal team-preset (Wave 0) остаётся однослойным:**

```
Horizontal template (Wave 0):
  Coordinator (top-level orchestrator)
    ├── Researcher
    ├── Writer
    └── Analyst
```

### Master-Agent responsibilities

| Responsibility | Master-Agent | Coordinator |
|---|---|---|
| Понимать domain-терминологию ниши | ✅ owner | inherits via context |
| Знать vertical workflow / ritual catalog | ✅ owner | none |
| Принимать стратегические решения (что вообще делать) | ✅ owner | follows Master's plan |
| Декомпозировать стратегию в operational sub-tasks | ✅ initial decomposition | ✅ tactical breakdown |
| Назначать конкретных specialists на sub-tasks | shares with Coordinator | ✅ owner |
| Управлять делегированием depth, cost, cancel | none | ✅ owner |
| Финальная сборка артефактов user-у | ✅ owner | feeds outputs к Master |
| Проверять качество с domain-perspective | ✅ owner | none |
| Triggering vertical rituals (Wave 3+) | ✅ owner | none |

### Routing pattern для vertical task

```
User → Master-Agent.handle_user_message(message):
  1. Master interprets user-prompt через domain-lens
  2. Master forms strategic plan (1–3 high-level objectives)
  3. Master delegates каждый objective к Coordinator с strategic context
  4. Coordinator decomposes objective в operational sub-tasks
  5. Coordinator assigns sub-tasks к specialists (Researcher, Writer, Analyst, vertical-specifics)
  6. Specialists return artifacts
  7. Coordinator returns aggregated result к Master
  8. Master synthesizes final user-facing artifact с domain-quality-check
  9. Master returns final response к user
```

### Cost & latency budget

- **+1 LLM-call** per task (Master-Agent layer) над horizontal baseline
- **~+15–20% tokens** per task (Master interpretation + final synthesis)
- **~+1–3 sec latency** per task (sequential Master call before/after Coordinator chain)
- **Pricing-rationale:** vertical-pricing-tier-rationale = Master-Agent layer + vertical MCPs + domain-memory (Wave 3 PARA) — все vertical-specific add-ons бандлуются в vertical-tier

### Master-Agent model selection

| Wave | Model для Master | Rationale |
|---|---|---|
| W1 | DeepSeek-R1 | Reasoning-heavy для strategic planning |
| W3+ | DeepSeek-R1 + vertical-knowledge memory (PARA Workspace) | Master читает «Знания команды» как primary context per [ADR-011](./ADR-011-memory-2-level.md) и [ADR-019](./ADR-019-vertical-autonomous-mode.md) |
| W4+ | Per cell choice (BYOK premium) | Enterprise может выбрать Claude/GPT для Master |

### Implementation outline

```python
# backend/src/agents/master.py
class MasterAgent:
    def __init__(self, cell: Cell):
        self.cell = cell
        self.vertical = cell.template.vertical_tag   # 'wb_seller' | 'agency_marketing_ru' | ...
        self.system_prompt = load_master_prompt(self.vertical)   # contracts/role-prompts/masters/<vertical>.md
        self.coordinator = cell.get_coordinator()
        self.llm = LLMRouter.choose("master", cell)

    async def handle_user_message(self, message: str) -> MasterResponse:
        # 1. Master analyses через domain-lens
        # 2. Forms strategic objectives list
        # 3. Delegates каждый objective к Coordinator (parent_task_id chain)
        # 4. Awaits aggregated results from Coordinator
        # 5. Domain-quality-check on output
        # 6. Synthesizes final user-facing artifact
        # 7. Returns MasterResponse
```

### Master-Agent prompt storage

Per [contracts/role-prompts/](../contracts/role-prompts/) pattern из Phase 00.5 deliverable:

```
.planning/contracts/role-prompts/
├── coordinator.md           # horizontal Coordinator (Wave 0)
├── researcher.md            # horizontal Researcher (Wave 0)
├── writer.md                # horizontal Writer (Wave 0)
├── analyst.md               # horizontal Analyst (Wave 0)
└── masters/                 # Wave 1+ vertical Masters
    ├── agency-marketing-ru-master.md
    ├── telegram-creator-master.md
    ├── wb-seller-master.md         # Wave 2
    ├── accounting-ip-master.md     # Wave 3
    └── smb-sales-master.md         # Wave 3
```

### Wave 1 phase 01.1 retrofit task

Wave 1 phase 01.1 («Расширение каталога: +2 vertical-templates») получает в scope:

- **Mini-task: Coordinator API retrofit под subordinate role.** Coordinator должен уметь:
  - принимать `strategic_context` поверх `user_prompt` (от Master)
  - возвращать aggregated result в Master-friendly format
  - track parent_task_id chain через Master → Coordinator → specialists
- **Mini-task: MasterAgent base class + 2 vertical instantiations** (Marketing-agency + Telegram-крейтор)
- **Mini-task: Master prompts (deep, 9-section, как horizontal-role prompts из Phase 00.5)**

Estimated: +5–7 дней к scope phase 01.1.

## Consequences

- ✅ **Vertical-pricing-rationale:** Master-Agent layer = primary differentiation для vertical-tier pricing над horizontal-tier
- ✅ **Domain-expertise modularity:** ниша-знания изолированы в Master, не размазаны по specialists
- ✅ **Future-extensibility:** Wave 3 «Vertical Rituals» + «Знания команды» (PARA) подключаются именно к Master-у, не к Coordinator
- ⚠️ **+15–20% tokens & ~+1–3 сек latency** per vertical task → влияет на TTFV для vertical-trials (Wave 2 metric ≤3 min — мониторим)
- ⚠️ **Coordinator API retrofit** = phase 01.1 +5–7 дней
- ⚠️ **Risk R-04 (runaway costs):** Master-Agent loop через Coordinator может cascading. Per-task hard-cap budget (50 T-credits) применяется к Master+children-chain совокупно, не per agent. Phase 01.1 acceptance criteria explicitly cover это
- 🔮 **Wave 3 PARA Workspace** становится canonical memory-backend для Master-Agents
- 🔮 **Wave 4 vertical-marketplace** строится на Master-Agent paradigm — third-parties контрибутят vertical-Master-промпты

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| Master-Agent **везде** (включая horizontal) | Унифицированный паттерн с дня 1 | +15–20% cost для horizontal, который не имеет vertical-knowledge для хранения | Phase 00.5 timebox + horizontal не требует domain-layer |
| Master-Agent **вместо** Coordinator | Двухслойная (а не трёхслойная) схема | Ломает [ADR-022](./ADR-022-coordinator-wizard-llm-hybrid.md) wizard-flow + Coordinator-skill теряется | ADR-022 — accepted, переписывать дорого |
| Master-Agent опционально per template | Flexibility | Архитектурный fragmentation — каждый template сам решает structure | Confusing debugging, ↑ surface для bugs |
| Vertical-knowledge в Coordinator system-prompt | Минимум кода | Coordinator system-prompt раздувается до 5–10K слов per vertical → token-cost ↑ + maintainability ↓ | Не масштабируется на 5 verticals |

## Links

- Risks: [R-02](../risks/REGISTER.md) (vertical-template quality), [R-04](../risks/REGISTER.md) (runaway costs), [R-32](../risks/REGISTER.md) (Master-Agent cost/latency overhead, opened с этим ADR)
- Phase: 01.1 (Marketing-agency + Telegram-крейтор Masters), 02.1 (WB-Селлер Master + Mini App), 03.1 (Master + PARA-memory integration)
- Related ADRs:
  - [ADR-016](./ADR-016-team-first-ux.md) — team-first UX (Master-Agent остаётся в рамках «команды»)
  - [ADR-017](./ADR-017-vertical-templates.md) — vertical-templates как primary USP (Master-Agent роль добавляется к составу)
  - [ADR-022](./ADR-022-coordinator-wizard-llm-hybrid.md) — Coordinator wizard-LLM hybrid (Coordinator теперь = COO в verticals)
  - [ADR-011](./ADR-011-memory-2-level.md) — memory (Wave 3 PARA становится Master-memory)
  - [ADR-019](./ADR-019-vertical-autonomous-mode.md) — vertical rituals (триггерятся Master-Agent в Wave 3+)
  - [ADR-030](./ADR-030-telegram-business-api.md) — Telegram Business API (consumed Telegram-крейтор Master-Agent в Wave 1; Marketing-agency Master через DM-management workflow)
