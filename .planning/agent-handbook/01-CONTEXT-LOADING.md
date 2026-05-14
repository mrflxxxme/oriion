# 01-CONTEXT-LOADING — Эффективная работа с context

> **Цель:** максимально использовать token-budget. Каждый файл, который ты не загружаешь, освобождает место для actual работы (генерации кода / анализа).

## Princip: Just-In-Time loading

**Не загружай превентивно.** Грузи когда конкретно понадобилось.

### Bad: Load-everything-first
```
1. Read PROJECT.md (3KB)
2. Read all 28 ADR (~70KB)
3. Read full glossary (8KB)
4. Read full stack.md (8KB)
5. Read risks/REGISTER.md (20KB)
6. Read phase-spec (5KB)
Total: 104KB загружено, 95% не нужно
```

### Good: JIT loading
```
1. Read README (3KB) — ориентация
2. Read STATUS (4KB) — где мы
3. Read phase-spec (5KB) — текущая задача
4. При встрече "see ADR-008" → read ADR-008 (3KB)
5. При встрече "use config from stack.md → Postgres" → grep stack.md by "Postgres" (1KB)
Total: ~16KB загружено, всё use'нул
```

## Token budgets для типовых задач

| Тип задачи | Target tokens loaded |
|---|---|
| Простая правка кода (1 файл, 50 строк) | 5-10 KB |
| Имплементация одного endpoint | 10-20 KB |
| Имплементация phase целиком | 30-60 KB |
| Архитектурная работа над модулем | 40-80 KB |
| Cross-phase интеграция | 60-120 KB |
| Крупный refactor | 100+ KB (используй subagents!) |

**Если приближаешься к 120KB context — рассмотри:**
1. Делегирование часть в subagent (свежий context)
2. Сохранить state в handoff-note и продолжить в новой session
3. Использовать summary-tools вместо full file reads

## Стратегии loading

### Strategy 1: Read with offset/limit

Для длинных файлов (ADR, phase-spec >200 строк) не читай целиком:

```python
# Bad: full read
Read(file_path="...ADR-002-llm-gateway.md")  # 200 lines

# Good: targeted offset
Read(file_path="...ADR-002-llm-gateway.md", offset=80, limit=40)  # only relevant section
```

### Strategy 2: Grep before Read

Если ищешь конкретный термин — Grep, не Read:

```python
# Bad: read full glossary
Read("../_meta/glossary.md")  # 200 lines

# Good: grep + targeted
Grep(pattern="Vertical-template", path="_meta/glossary.md", output_mode="content")
```

### Strategy 3: Symbol-search instead of file-tree

Если ищешь где определён символ/функция/класс:

```python
# Bad: glob through all files
Glob("**/*.py")

# Good: grep symbol definition
Grep(pattern="^class Coordinator", glob="*.py")
```

### Strategy 4: Skip ARCHIVE / closed docs

Не читай:
- `archive/*` — историческое, не active state (если только не нужна история revisions)
- `research/teamly_to_analysis/*` — completed analysis, читай только если делаешь cross-reference
- Closed risks (R-13, R-15, R-29) — не релевантны для active work

## Context priority matrix

| Priority | Когда читать |
|---|---|
| **P0 (always)** | README.md (1×/session), STATUS.md (1×/session) |
| **P1 (task-start)** | Текущий phase-spec, 00-START-HERE.md (1×/session) |
| **P2 (on reference)** | Цитируемые ADR, цитируемые risks |
| **P3 (on lookup)** | glossary.md, stack.md, conventions.md — точечный grep |
| **P4 (rare)** | Other ADR (не цитированные), other phases, agent-handbook (не текущий) |
| **P5 (avoid)** | archive/, research/ unless explicit need |

## Sub-prompt для long-context подзадач

Если задача требует много context, делегируй subagent с тем же подходом:

```python
# Pseudocode для main agent
Agent(
    subagent_type="general-purpose",
    description="Implement Phase 00.4 LLM-gateway",
    prompt="""
    Your task: implement Phase 00.4 (LLM gateway).
    
    REQUIRED reading (in order):
    1. .planning/roadmap/wave-0-foundation/phases/00.4-llm-gateway.md
    2. .planning/decisions/ADR-002-llm-gateway.md
    3. .planning/decisions/ADR-018-deepseek-primary-llm.md
    4. .planning/_meta/stack.md (section "LLM-провайдеры" only)
    
    DO NOT load:
    - Other phases
    - Other ADRs
    - Full glossary
    
    Implementation requirements: <specific tasks>
    """
)
```

## Memory & Notes

Используй TodoWrite tool для tracking own progress в complex task:

```python
TodoWrite([
    {"content": "Read phase 00.4 spec", "status": "completed", ...},
    {"content": "Setup deepseek client", "status": "in_progress", ...},
    {"content": "Add yandex provider", "status": "pending", ...},
])
```

Это **снимает burden** с context window — не нужно постоянно повторять «что я делаю», TodoWrite держит state.

## Файл сводок / cheatsheets

Для часто используемых references:

| Cheatsheet | Загружай |
|---|---|
| Tech versions (FastAPI version, React version, ...) | `_meta/stack.md` (grep) |
| Domain terms | `_meta/glossary.md` (grep) |
| Code conventions | `_meta/conventions.md` (grep) |
| Subagents capabilities | `agent-handbook/02-DELEGATION.md` |
| Bash commands | `_meta/conventions.md` (раздел "Process") |

## Anti-pattern: лишние reads

❌ **Не читай ADR пока не цитируется.** Если phase-spec не упоминает ADR-007, не читай ADR-007.

❌ **Не grep с слишком широким pattern.** `Grep("a")` — бесполезно. Конкретнее.

❌ **Не повторно читай тот же файл.** Tool harness кеширует state — после Read'a файл уже в твоём context. Перечитывай только если файл был edited.

## Расширение context при необходимости

Если задача оказалась сложнее ожидаемого:

1. **Сначала используй CtPtрл-F (grep)** в уже загруженных файлах
2. **Затем targeted read** новых файлов с offset/limit
3. **Затем full read** только если нет другого пути
4. **Затем делегирование** в subagent с свежим context
5. **Crowning resort:** spawn новую session с handoff-notes

## Quick reference

```
P0: README + STATUS (always, ~7KB)
P1: phase-spec + START-HERE (task-start, +8KB)
P2: cited ADRs (on-reference, +3KB each)
P3: glossary/stack grep (on-lookup, +1KB each)
P4: other ADRs/phases (rare, skip)
P5: archive/research (avoid, skip)
```

**Typical session budget: 15-30 KB loaded, 80-100 KB available для работы.**
