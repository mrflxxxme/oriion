# ADR-022: Coordinator — Wizard (free) + LLM (trial/paid) гибрид

- **Status:** Accepted

## Decision

### Free-tier (без регистрации): Wizard

Landing page `/`:
- Pixel-аватар Coordinator + speech bubble «Какую задачу хотите решить?»
- 3-step wizard (rule-based, NOT LLM):

**Step 1: «Что хотите делать?»** (visual cards с emoji)
- 🛒 Продавать на маркетплейсах (WB / Ozon)
- 📈 Маркетинг и контент
- ✍️ Развивать Telegram-канал / Курсы
- 💼 Вести бухгалтерию ИП
- 🎯 Работа с CRM / Продажи
- 🎨 Что-то другое

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

**Coordinator — НЕ generic, а per-vertical fine-tuned:**

**WB-Селлер Coordinator:**
```
Ты — Координатор команды WB-Селлера. Помогаешь владельцу магазина на WildBerries.

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
- Phase: 00.5 (initial Coordinator), 01.9 (wizard onboarding), 02.5 (full onboarding with all templates)
- Related ADRs: ADR-002 (LLM gateway), ADR-016 (team-first), ADR-017 (vertical-templates)
