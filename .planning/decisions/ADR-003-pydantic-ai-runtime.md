# ADR-003: Pydantic-AI как агентный runtime

- **Status:** Accepted

## Decision

**Pydantic-AI** как ядро runtime + собственный тонкий слой `Team / Role / Coordinator`, моделирующий продуктовую метафору. Не зависим от CrewAI/LangGraph напрямую.

## Implementation

- Pydantic-AI Agent per role (system_prompt + tools + model)
- Native MCP-support через `pydantic-ai` SDK
- Streaming responses
- Tool-use (function calling)
- Structured output через Pydantic-модели

## Custom layer

```
backend/src/agents/
├── team.py              # Team aggregate: collection of agents + workflow
├── role.py              # Role definition
├── coordinator.py       # Coordinator-as-router logic
├── agent_instance.py    # Agent в конкретной cell
└── runtime/
    ├── task_executor.py # execute Task через Pydantic-AI Agent
    ├── delegate.py      # delegate_task tool (Coordinator → sub-agent)
    └── streaming.py     # SSE для real-time прогресса
```

## Consequences

- Type-safe граница между ролями
- AI-dev-agents знают Pydantic-AI наизусть (актуальный fresh framework)
- Полный контроль над оркестрацией (Coordinator + workflow templates)

## Links

- Phase: 00.5 (initial runtime), 01.1 (Coordinator + sub-task), 03.2 (workflow templates)
- Related ADRs: ADR-001 (Python monolith), ADR-011 (memory), ADR-013 (MCP)
