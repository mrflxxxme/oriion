# ADR-022: Coordinator — Wizard (free) + LLM (trial/paid) гибрид

- **Status:** Accepted (revision: 2026-05-15 — Coordinator role formally bifurcated по horizontal vs vertical preset per [ADR-029](./ADR-029-master-agent-vertical-templates.md))

## Hierarchy positioning (revision 2026-05-15)

Coordinator role играет разную роль в horizontal vs vertical presets:

| Preset тип | Wave | Top-level | Coordinator role |
|---|---|---|---|
| **Horizontal** (`productivity-core`) | W0+ | **Coordinator** (no Master) | Top-level orchestrator — принимает user-prompt напрямую, декомпозирует, делегирует specialists |
| **Vertical** (5 templates) | W1+ | **Master-Agent** (per [ADR-029](./ADR-029-master-agent-vertical-templates.md)) | Operational COO — subordinate к Master, принимает strategic-context от Master, декомпозирует в operational sub-tasks, назначает specialists |

В vertical-mode Coordinator API расширяется (phase 01.1 retrofit task):
- Принимает `strategic_context: dict` поверх `user_prompt: str`
- Возвращает `aggregated_result` в Master-friendly Pydantic format
- Track `parent_task_id` chain через Master → Coordinator → specialists (depth +1 vs horizontal)

## Decision

### Free-tier (без регистрации): Wizard

Landing page `/`:
- Pixel-аватар Coordinator + speech bubble «Какую задачу хотите решить?»
- 3-step wizard (rule-based, NOT LLM):

**Step 1: «Что хотите делать?»** (visual cards с emoji)
- 🧰 Универсальные задачи (исследования, аналитика, контент) → routes к `productivity-core` (horizontal, Wave 0+)
- 📈 Маркетинг-агентство для клиентов → routes к `agency_marketing_ru` (vertical, Wave 1+)
- ✍️ Развивать Telegram-канал / Курсы → routes к `telegram_creator` (vertical, Wave 1+)
- 🛒 Продавать на маркетплейсах (WB / Ozon) → routes к `wb_seller_v1` (vertical, Wave 2+)
- 💼 Вести бухгалтерию ИП → routes к `accounting_ip` (vertical, Wave 3+)
- 🎯 Работа с CRM / Продажи → routes к `smb_sales_ru` (vertical, Wave 3+)

⚠️ **Wizard Wave 0:** только `productivity-core` доступен. Карточки для verticals показываются с лейблом «Скоро» — клик регистрирует waitlist-entry. Полный routing активируется поэтапно (W1 → 2 vertical, W2 → +WB, W3 → +ИП-Бух +СМБ-Sales).

**Step 2: «Размер вашей команды?»**
- Один я
- Маленькая команда (2-5 чел)
- Растущая команда (6-15 чел)
- Большая команда (15+)

**Step 3: «Главная задача на этой неделе?»** (textarea)
- Используется как «first task draft» для onboarding

**CTA:** «Создать команду бесплатно (14 дней триал)» → Registration

### Trial-tier (14 дней, 500 кредитов): LLM-Coordinator

После регистрации → auto-spawn trial-cell с pre-selected template (по wizard answer Step 1) + 500 кредитов.

**Coordinator превращается в LLM-driven:**
- Pixel-аватар в Cell-dashboard
- Free-form chat: «Что сделать?»
- Понимает natural language
- Decomposes задачу → creates Task → assigns правильному агенту в cell
- Vertical-aware prompts (см. ниже)

**Onboarding sequence:**
```
Регистрация → email-verify → 
Auto-spawn trial-cell с pre-selected team (на основе wizard) → 
Coordinator: "Привет! Я Координатор твоей команды <Team Name>.
              Ты сказал, что хочешь '<wizard step 3 text>'. 
              Готов помочь?" → 
[Yes] / [Уточнить] →
Coordinator decomposes → assigns → first task running → 
[Live progress в Pixel Department] → 
First artifact ready → wow-moment
```

**TTFV target:** <3 минуты от register-submit до первого artifact.

**Credit-limit guardrail (R-25):**
- 500 кредитов hard-cap для trial
- При <50 left → in-app notification «Осталось 47 кредитов»
- При 0 → soft-block с paywall: «Trial завершён. Подключите тариф для продолжения»

### Paid-tier: Full LLM-Coordinator

- Все возможности trial + расширения:
- Workflow templates (Wave 3+)
- Vertical rituals access
- Cross-team coordination (если несколько cells)

### Coordinator's model selection

| Wave | Model | Rationale |
|---|---|---|
| W0-1 | DeepSeek-V3 | Cheapest для Coordinator's task decomposition |
| W2-3 | DeepSeek-R1 для complex (5+ step) decomposition | Better reasoning при больших задачах |
| W4+ | Choice per cell (user can select) | Premium clients могут выбрать Claude/GPT через BYOK |

### Vertical-aware Coordinator prompts

**Coordinator — НЕ generic, а per-preset fine-tuned. Промпт-контракты хранятся в [`contracts/role-prompts/`](../contracts/role-prompts/):**

| Preset | Coordinator prompt | Top-level over Coordinator |
|---|---|---|
| `productivity-core` (W0+) | `contracts/role-prompts/coordinator.md` | — (top-level itself) |
| `agency_marketing_ru` (W1+) | `contracts/role-prompts/masters/agency-marketing-ru-master.md` + Coordinator inherits | Master-Agent |
| `telegram_creator` (W1+) | similar to above | Master-Agent |
| `wb_seller_v1` (W2+) | similar | Master-Agent |
| `accounting_ip` (W3+) | similar | Master-Agent |
| `smb_sales_ru` (W3+) | similar | Master-Agent |

В vertical-mode Coordinator-промпт остаётся короче (operational/tactical layer), а domain-knowledge и strategic-context живут в Master-Agent промпте per [ADR-029](./ADR-029-master-agent-vertical-templates.md).

**WB-Селлер Coordinator (Wave 2+, subordinate к Master-Agent):**
```
Ты — Координатор команды WB-Селлера. Operational COO под Master-Agent.

Знаешь:
- WB-терминологию (FBO, FBS, артикул, поставка, остатки, выкуп, рейтинг)
- Workflow селлера (поставки → продвижение → продажи → отзывы)
- РФ-маркетплейсы (Wildberries, Ozon, Yandex Market)
- Что важно селлеру (конверсия, маржинальность, остатки)

В твоей команде:
- Listing Writer (Марк) — пишет описания товаров, заголовки
- Researcher (Скаут) — анализирует конкурентов, ниши, цены
- Analyst (Виктор, Wave 1+) — аналитика продаж через Pyodide
- SMM (Анастасия, Wave 2+) — контент для Telegram-канала

При получении задачи:
- Понимаешь, какой агент справится лучше
- Создаёшь sub-tasks с чёткими instructions
- При сложных задачах (5+ шагов) — показываешь план владельцу перед exec
- Если задача вне scope (например, технический вопрос) — честно говоришь «это вне моей экспертизы»
```

Аналогично для остальных 4 vertical-templates.

**Productivity-core Coordinator (Wave 0+, top-level horizontal):**

Полный prompt — в [`contracts/role-prompts/coordinator.md`](../contracts/role-prompts/coordinator.md). 9-секционная глубокая структура:
1. Role identity & mission (top-level orchestrator для horizontal preset)
2. Behavioral instructions (decomposition heuristics, delegation patterns)
3. Output format contracts (Pydantic CoordinatorOutput per Phase 00.5)
4. Quality standards
5. Anti-patterns & guardrails
6. Few-shot examples (включая demo-сценарий «Market & content brief»)
7. Domain-aware vocabulary (project-management, RACI, RU-business)
8. Handoff protocols (как parent для Researcher/Writer/Analyst)
9. Self-evaluation prompts (cycle-detection, orphan-task check, cost-cap check)

Status: Proposed first-draft (Phase 00.5). Hardening pass — Phase 01.1 retro.

### Implementation

```python
# backend/src/agents/coordinator/
class Coordinator:
    def __init__(self, cell: Cell):
        self.cell = cell
        self.vertical = cell.template.vertical_tag
        self.system_prompt = load_vertical_prompt(self.vertical)
        self.team = cell.get_agents()
        self.llm = LLMRouter.choose("coordinator", cell)
    
    async def handle_user_message(self, message: str) -> CoordinatorResponse:
        # 1. LLM analyses message + decomposes if needed
        # 2. Returns: {clarification_needed | plan | direct_action}
        # 3. If plan: enumerates tasks with agent assignments
        # 4. User confirms (UI checkbox) → creates Task entities
        # 5. If clarification: asks back to user
        # 6. If direct_action: creates single Task immediately
```

### UI

**Pixel Department / Cell dashboard:**
- Coordinator-аватар в чате (right sidebar или modal)
- Chat input bottom + history scroll
- Inline plan-preview перед execution
- Task-status updates flow в chat (как notifications)

### Free-tier vs Trial vs Paid (summary)

| Tier | Coordinator |
|---|---|
| Free (unauth) | Wizard (3 steps) — convert to trial |
| Trial (14 days, 500 credits) | LLM-driven, vertical-aware, credit-limited |
| Paid | LLM-driven + workflow templates + rituals (Wave 3+) |

## Consequences

- Free-tier cost = 0 (wizard rule-based)
- Trial-юзер видит реальную работу team — высокая conversion
- Vertical-aware Coordinator = domain expertise
- Pre-filled first task из wizard → TTFV <3 мин

## Links

- Risks: [R-25](../risks/REGISTER.md), [R-26](../risks/REGISTER.md)
- Phase: 00.5 (initial Coordinator for horizontal productivity-core), 01.1 (Coordinator retrofit for subordinate-to-Master mode per ADR-029), 01.9 (wizard onboarding routing horizontal vs vertical), 02.5 (full onboarding с WB-vertical + Mini App)
- Related ADRs: ADR-002 (LLM gateway), ADR-016 (team-first), [ADR-017](./ADR-017-vertical-templates.md) (vertical-templates + horizontal anchor), [ADR-029](./ADR-029-master-agent-vertical-templates.md) (Master-Agent layer over Coordinator in verticals)
