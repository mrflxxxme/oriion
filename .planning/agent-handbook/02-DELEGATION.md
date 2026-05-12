# 02-DELEGATION — Карта subagents + правила делегирования

> **Цель:** использовать subagents на полную. Каждое делегирование освобождает main-agent context + распараллеливает работу.

## Когда делегировать

✅ **Делегируй**:
- Многошаговая исследовательская работа (исследование codebase, grep по сотням файлов)
- Изолированная задача с известным input → output (e.g. «напиши тесты для X»)
- Параллельные independent tasks (запусти 3 subagent одновременно)
- Длительная аналитика (browser-automation, network captures, web research)
- Code-review (отдельный contextual взгляд)
- Security audit / compliance check (specialized perspective)

❌ **НЕ делегируй**:
- Тривиальная замена (1 файл, <50 строк) — быстрее самому
- Архитектурное решение (нужен ваш domain-context)
- Decision-making (subagent предлагает, ты решаешь)
- Final approval / merge (это ваша ответственность)

## Subagent catalog (curated для нашего проекта)

### Core development

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **general-purpose** | Multi-step research, code-search, complex tasks | Default-выбор для unknown territory |
| **backend-dev** | Backend API development with pattern learning | Wave 0+ — implement endpoints, FastAPI work |
| **coder** | Clean efficient code writing | Конкретные modules, classes, helpers |
| **Frontend Developer** | React/Vite/TanStack expert | Frontend work, UI components |
| **Senior Developer** | Premium implementation (Laravel/CSS/Three.js) | Сложные frontend tasks |

### Quality & Review

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **code-reviewer** | Severity-rated code review with logic defect detection | На каждый non-trivial PR (Tier 3+) |
| **oh-my-claudecode:code-reviewer** | Code-style + SOLID + performance | Альтернатива выше |
| **reviewer** | Self-learning code review с pattern detection | После coder finishes |
| **analyst** | Code quality analysis | Перед refactor / для tech-debt assessment |
| **Code Reviewer** | Constructive feedback (correctness/maintainability/security) | Финальный код-ревью перед merge |

### Testing

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **tester** | AI-powered test generation | Создать тесты для new code |
| **API Tester** | API validation, performance testing | Wave 1+ API contract validation |
| **oh-my-claudecode:test-engineer** | Test strategy + flaky-test hardening | Test architecture |
| **tdd-london-swarm** | Mock-driven TDD development | Для test-driven new code |

### Security

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **security-auditor** | Vulnerability detection + CVE search + compliance | Tier 4 PR + перед public-launch |
| **Security Engineer** | Threat modeling + vulnerability assessment + secure code review | Архитектурный security review |
| **oh-my-claudecode:security-reviewer** | OWASP Top 10 + secrets + unsafe patterns | Каждый PR с auth/payment/data |
| **Blockchain Security Auditor** | Smart contract audit | НЕ для нас (нет blockchain) |
| **pii-detector** | PII leak scanning | После работ с personal data |
| **Compliance Auditor** | SOC 2 / ISO 27001 / HIPAA audits | Wave 4+ Enterprise readiness |

### Architecture & Design

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **Software Architect** | System design + DDD + patterns | Архитектурные решения, новые ADR |
| **Backend Architect** | Scalable system design / DB / API | Backend architecture deep-dive |
| **system-architect** | High-level technical decisions | Cross-boundary решения |
| **adr-architect** | ADR documentation + pattern learning | Создание новых ADR |
| **ddd-domain-expert** | DDD + bounded contexts + aggregates | Domain modeling |
| **UX Architect** | Technical UX + CSS systems | Frontend architecture |

### DevOps

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **DevOps Automator** | Infrastructure automation + CI/CD + cloud ops | Setup phases, infrastructure |
| **cicd-engineer** | GitHub Actions pipeline creation | Wave 0.1 CI/CD setup |
| **Infrastructure Maintainer** | System reliability + performance | Wave 4+ scale |
| **release-manager** | Release coordination + deployment | Wave 3+ release management |

### Specialized

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **AI Engineer** | ML model development + AI integration | LLM-gateway work, agent runtime |
| **Database Optimizer** | Schema design + query optimization | Phase 00.3, scale phases |
| **Data Engineer** | Data pipelines + ETL/ELT + Spark/dbt | NOT для нас (small data) |
| **performance-engineer** | Flash Attention + WASM SIMD + token optimization | Optimisation work Wave 4+ |
| **MCP Builder** | MCP server development | Wave 2 для наших РФ-MCP-серверов |

### Planning & Research

| Subagent | Mandate | Когда использовать |
|---|---|---|
| **Plan** | Software architect agent для implementation plans | Перед сложными tasks |
| **Explore** | Fast read-only search agent для locating code | Для navigation существующего codebase |
| **researcher** | Deep research + information gathering | Tech research, library evaluation |
| **gsd-phase-researcher** | Research implementation before planning | Перед planning phase |
| **Trend Researcher** | Market intelligence + competitive analysis | Marketing decisions |

### Out of scope для нас (НЕ используем)

- Roblox / Unity / Unreal / Godot — мы НЕ игры
- Blender Add-on / Game Audio — мы НЕ media production
- Sales-focused (Deal Strategist / Outbound Strategist) — нет sales-team пока
- Indian/Korean/Chinese-specific — мы РФ-focused

## Delegation template

```
Agent(
    description="<3-5 word task description>",
    subagent_type="<exact subagent name>",
    prompt="""
    Your task: <one-sentence goal>.
    
    Context (minimal):
    - This is part of TEAMLY_RU project (см .planning/README.md if needed)
    - Current phase: Wave N Phase N.M (<phase-slug>)
    - Related ADR: ADR-XXX (cite specifically)
    
    REQUIRED reading (in order):
    1. <only files actually needed>
    2. <max 3-5 files>
    
    Specific requirements:
    1. <concrete requirement>
    2. <concrete requirement>
    3. <output format expected>
    
    Constraints:
    - DO NOT modify <files outside scope>
    - DO NOT load <large irrelevant files>
    - DO ask user before <architectural deviation>
    
    Deliverables:
    - <concrete artifacts: files, PR, summary>
    """,
    run_in_background=<true if parallel-able>
)
```

## Parallel execution

Для **independent tasks** — запускай в parallel в одном message:

```python
# Pseudocode — single message with multiple Agent calls
Agent(description="Implement LLM-gateway", subagent_type="backend-dev", ...)
Agent(description="Setup CI pipelines", subagent_type="cicd-engineer", ...)
Agent(description="Write tests for auth", subagent_type="tester", ...)
```

Это запустит **параллельно**, не sequentially.

## Background execution

Для long-running tasks используй `run_in_background=true`:
- Build & test pipelines
- Heavy refactors
- Security audits

Это **разблокирует main thread** для другой работы.

## Когда subagent возвращает что-то

1. **Прочитай результат** (внутри tool-call response)
2. **Verify** — не доверяй слепо, проверь критичные изменения через Read/Bash
3. **Synthesize** — если запускал 3 параллельно, объедини outputs
4. **Apply** или **escalate** к user'у (если subagent предложил что-то сомнительное)

## Anti-patterns

### ❌ Делегирование архитектурного решения
```
# Bad
Agent(description="Decide auth", prompt="Choose between custom JWT, Authentik, Keycloak")
```
Архитектурное решение требует **твоего понимания контекста**. Subagent даст generic answer без знания project-specific ADR.

### ❌ Делегирование без minimal context
```
# Bad
Agent(description="Implement feature", prompt="Add auth")  # too vague
```
Subagent потеряет много времени на orientation. Дай конкретный phase-spec + ADR refs.

### ❌ Перепоручение того же task разным subagent'ам параллельно
```
# Bad
Agent(description="Code A", subagent_type="coder", ...)
Agent(description="Code A", subagent_type="backend-dev", ...)  # дублирование
```
Один task — один subagent. Дублирование — пустая трата токенов.

### ❌ Отправка в subagent с большим всем-в-context
```
# Bad
Agent(prompt="Read entire .planning/ directory and implement X")
```
Subagent тоже имеет token-budget. Конкретизируй какие файлы read.

## Verification matrix

После работы subagent — проверь:

| Что | Как |
|---|---|
| Файлы созданы | `Glob("**/*.py")` или `Bash("git status")` |
| Тесты прошли | `Bash("pytest backend/tests/")` |
| Lint clean | `Bash("ruff check backend/")` |
| Type clean | `Bash("mypy --strict backend/")` |
| Security clean | `Bash("semgrep --config=auto")` |
| Existing functionality не сломана | smoke-tests |

**Если subagent утверждает «всё готово» — проверь, прежде чем верить.**

## Эскалация subagent → user

Если subagent сталкивается с архитектурной развилкой — он не должен решать сам. Patterns:
- В prompt: «If architectural ambiguity → ask, don't decide»
- В response: subagent возвращает «Found ambiguity at X, options A/B/C, recommend X for reasons Y»
- Main agent: prosumption ([`03-ESCALATION.md`](./03-ESCALATION.md))

## Cheatsheet

| Сценарий | Subagent |
|---|---|
| «Имплементируй endpoint» | backend-dev / coder |
| «Создай тесты для X» | tester / API Tester |
| «Review этот PR» | code-reviewer + security-auditor (parallel) |
| «Найди где определена функция Y» | Explore |
| «Setup CI/CD» | cicd-engineer + DevOps Automator (parallel) |
| «Design новый bounded context» | Software Architect + ddd-domain-expert |
| «Написать новый ADR» | adr-architect |
| «Найти security-уязвимость» | security-auditor + oh-my-claudecode:security-reviewer (parallel) |
| «Optimize slow query» | Database Optimizer |
| «Сделать MCP-сервер для Bitrix» | MCP Builder + backend-dev (sequential: MCP planning → implementation) |
