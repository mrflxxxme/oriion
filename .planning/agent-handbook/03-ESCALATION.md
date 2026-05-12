# 03-ESCALATION — Когда задавать вопрос user'у

> **Цель:** AI-агент работает максимально автономно, но **при неоднозначности останавливается и спрашивает**. Лучше спросить, чем сделать неправильно.

## Decision tree: «спрашивать или решать сам?»

```
Я столкнулся с неоднозначностью.
│
├─ Есть прямой ADR / phase-spec / convention, который отвечает?
│  └─ YES → действуй по нему, не спрашивай. (Reference в commit-message.)
│
├─ Есть конвенция в _meta/ или существующий pattern в codebase?
│  └─ YES → следуй convention. (Reference в commit-message.)
│
├─ Можно вывести из принципа "минимальность + простота"?
│  └─ YES → выбери простейший вариант, документируй в ADR если значимо.
│
├─ Вопрос архитектурный + затрагивает >1 bounded context?
│  └─ YES → ESCALATE. Создай ADR-proposal + спроси user'а.
│
├─ Вопрос затрагивает founder-territory (юр, деньги, brand, hiring)?
│  └─ YES → ESCALATE 100%. Это не твоё решение.
│
├─ Вопрос противоречит существующему ADR?
│  └─ YES → ESCALATE. Объясни conflict + предложи resolution.
│
├─ Вопрос имеет 2+ equally valid решения с разными trade-offs?
│  └─ YES → ESCALATE с recommendation + trade-offs.
│
└─ Иначе → действуй по best-judgment. Логируй reasoning в commit-message.
```

## Что НЕ требует escalation (просто реши)

- Naming variables, functions, files (следуй conventions.md)
- Имплементация по чёткому phase-spec
- Выбор между equivalent library версиями (выбирай latest stable)
- Решения которые **легко** обратимы (refactor если ошибся)
- Style / formatting (есть ruff/prettier)

## Что ВСЕГДА требует escalation

### Архитектурные

- Новый bounded context
- Замена tech-stack компонента (даже если ADR прямо не запрещает)
- Migration существующей таблицы / API contract
- Cross-cutting concerns (logging, error-handling, observability strategy)

### Юр / Compliance

- Любая работа с ПДн без чёткой схемы из ADR-014
- Tracking / analytics / consent flow (особенно после consent ФЗ-152)
- Storage / retention policy
- Content moderation rules
- Cross-border data transfer

### Деньги / Pricing

- Pricing changes
- New payment provider integration
- Refund logic edge cases
- Promo codes / discounts logic

### Бренд / UX

- Brand voice changes
- Tone of voice для customer-facing copy
- Visual design ставит (особенно vertical-героев)
- Pricing page wording

### Безопасность

- Изменение auth flow
- Permissions model changes
- New external integration (особенно если требует OAuth)
- Cryptography choices

## Формат escalation question

### Bad escalation

```
"Stuck on X. What to do?"
```

Слишком vague. User тратит время на reverse-engineering задачи.

### Good escalation template

```
## Контекст
Phase: <wave>.<phase> (<slug>)
Task: <one-sentence task>
ADR refs: <ADR-XXX if relevant>

## Развилка
<one paragraph: что неоднозначно, почему стоп>

## Варианты

### Option A: <name>
- ✅ Pro: ...
- ⚠️ Contra: ...
- 🕐 Effort: ...
- 🔮 Future: ...

### Option B: <name>
- ✅ Pro: ...
- ⚠️ Contra: ...
- 🕐 Effort: ...
- 🔮 Future: ...

### Option C: <name>  [опц.]
- ...

## Моя рекомендация: <A/B/C>

Логика: <2-3 предложения почему>

## Что заблокировано до решения

- <Phase X> — не могу продолжать без выбора
- <Risk Y> — потенциально материализуется при <бад выбор>

## Готов выполнить после решения

<ETA имплементации после ответа: 1 час / 1 день / 3 дня>
```

## Когда subagent escalate'ит к main-agent

Subagent НЕ должен сам решать architectural ambiguity. Pattern:

```
# В prompt subagent'a
"If you encounter architectural ambiguity:
1. DO NOT make a decision
2. Stop and return ESCALATION block with format above
3. Main agent will decide or escalate further to user"
```

Main-agent получает ESCALATION block, решает:
- **Если есть clear path** (например, ADR-XXX даёт direction) → instruct subagent продолжать с указанием
- **Если архитектурная развилка** → escalate к user'у

## Когда AI-агент НЕ должен escalate (anti-patterns)

### ❌ Каждое решение к user'у
Don't: «Какое имя дать функции?». Use convention.
Don't: «Использовать List или Tuple?». Use Pydantic + PEP-484.

User теряет время. AI-агент должен принимать **80% решений сам**.

### ❌ Escalation без recommendation
Don't: «Что выбрать: A или B?». User не контекст-loaded.
Do: «Рекомендую A. Контекст: ... Trade-off: ...».

### ❌ Параллельные escalations
Don't: 5 escalation в одном messaqge.
Do: Block на первой → answer → продолжение.

### ❌ Escalation без блокировки
Don't: спросить и продолжать «авансом».
Do: остановиться, дождаться ответа, потом продолжить.

## Лимиты для нашего проекта

| Тип решения | Кто решает |
|---|---|
| Code style | AI-agent (conventions.md) |
| Library choice (in-stack) | AI-agent (stack.md) |
| New library / dependency | Tech Lead (review PR) |
| Refactor in-bounded-context | AI-agent (минимизация, document) |
| Cross-context refactor | Tech Lead (review) |
| New ADR proposal | AI-agent создаёт draft, Tech Lead/Founder approve |
| Vertical-template prompts | Founder (domain expertise) |
| Pricing changes | Founder |
| Marketing copy | Founder + Marketing |
| Security policy change | Tech Lead + Founder |
| Major migration | Founder approve, Tech Lead implement |

## Escalation log

После эскалации — записать в STATUS.md:
- Дата escalation
- Кто escalated
- Resolution + ADR (если архитектурное)
- Lessons learned (если хорошо описаны trade-offs)

Это позволяет видеть **какие архитектурные развилки** возникают и улучшать decision-making в будущих фазах.

## Связь с handbook'ом

- При не уверен где найти context → [`01-CONTEXT-LOADING.md`](./01-CONTEXT-LOADING.md)
- При нужно делегировать subagent → [`02-DELEGATION.md`](./02-DELEGATION.md)
- При уверен в решении и продолжаешь → [`04-HANDOFF.md`](./04-HANDOFF.md) (для записи в STATUS)

## Cheat sheet

| Ситуация | Action |
|---|---|
| Phase-spec явно описывает что делать | ✅ Делай (cite phase-spec в commit) |
| Чёткий ADR | ✅ Следуй ADR (cite в commit) |
| Существующий pattern в codebase | ✅ Следуй pattern (consistency win) |
| 2 равноценных варианта без preference | ⚠️ Выбери простейший, document |
| Architectural ambiguity (cross-bounded) | 🛑 ESCALATE |
| Founder-territory (юр/деньги/бренд) | 🛑 ESCALATE always |
| Conflict с ADR | 🛑 ESCALATE с proposal |
| Phase scope expanding | 🛑 ESCALATE (scope creep risk R-12) |
