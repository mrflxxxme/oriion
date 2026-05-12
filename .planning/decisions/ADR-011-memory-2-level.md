# ADR-011: Memory — двухуровневая (cell + role) + persistent в Wave 2 + «Знания команды» в Wave 3

- **Status:** Accepted

## Decision

### Wave 1: Двухуровневая memory

**Cell memory** — общая база знаний команды cell
- Документы, факты о компании, glossary
- Доступна всем агентам в cell через RAG
- Хранение: pgvector в `cell_<uuid>.memory_entries`
- HNSW index на embedding (1024 dim — YandexGPT Embeddings)

**Role memory** — личная память каждого agent-instance
- Предпочтения пользователя, стилевые/процессные паттерны
- Хранение: pgvector в `cell_<uuid>.role_memory_entries` с `agent_id` фильтр

**Manual control:**
- UI-панель «Что помнит [агент]» — view/edit/delete entries
- Tool-output НЕ сохраняется в memory автоматически
- Только результат обработки агентом + явный «запомни» от пользователя ИЛИ через filter-agent

**Filter-agent:**
- LLM-вызов с lite-моделью (yandexgpt-lite / deepseek-v3) после task complete
- Решает «достойно ли это запоминания + что именно»
- Cost: ~0.01-0.05 кредитов per call

### Wave 2: Persistent memory across sessions

- Memory entries не TTL-привязаны к сессии
- Conversation history per agent (последние N=50 сообщений как FIFO + summary)
- **Conversation summary:** при превышении лимита context — LLM генерирует короткое summary (~500 токенов) → saved как memory_entry с tag=`conversation_summary`
- При новом запросе агент получает: relevant memories (RAG) + recent summary + current task

**Persistence storage:**
- Memory entries: pgvector
- Conversation history: `cell_<uuid>.conversation_history` (jsonb + partitioned by month)
- Conversation summaries: pgvector с special tag

### Wave 3: «Знания команды» (PARA Workspace)

4 категории (русские названия):

| Категория | Назначение |
|---|---|
| **Проекты** | Активные задачи с deadline |
| **Сферы** | Долгосрочные направления без чёткого завершения |
| **Ресурсы** | Справочные материалы, доки, шаблоны, brand book |
| **Архив** | Completed projects, outdated resources |

**UX:**
- Panel в Cell-dashboard, 4 вкладки
- Каждая entry — enriched memory_entry с category, title, body, tags, references
- Drag-and-drop между категориями
- Auto-archive: completed projects → Архив; outdated resources (>1 год без access) → suggested archive

**Auto-population по rituals:**
- `nightly-consolidation` (cron Daily 2:00 AM): анализирует сессии за день, suggest new entries
- `morning-briefing` (cron Daily 8:00 AM): прогон через Проекты с deadline → утренний дайджест

### Retention & cleanup

- Cell memory entries старше 1 года → автоархив с уведомлением owner
- Role memory — без auto-expiry, только manual cleanup
- Conversation history — retention 90 дней default, settable per cell
- Архив (PARA) — не удаляется автоматически

### Privacy

- Memory entries содержащие ПДн → tagged + audit-logged
- При delete user account → cascading delete всех memory entries
- При delete cell → 30-day grace period → permanent delete

### API endpoints

```
GET    /api/cells/<id>/memory                  # list cell memory
POST   /api/cells/<id>/memory                  # manual add
DELETE /api/cells/<id>/memory/<entry_id>       # delete

GET    /api/cells/<id>/agents/<aid>/memory     # role memory
POST   /api/cells/<id>/agents/<aid>/memory
DELETE /api/cells/<id>/agents/<aid>/memory/<entry_id>

# Wave 3 PARA
GET    /api/cells/<id>/knowledge?category=projects
POST   /api/cells/<id>/knowledge
PATCH  /api/cells/<id>/knowledge/<entry_id>    # move category, edit
DELETE /api/cells/<id>/knowledge/<entry_id>
```

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-19](../risks/REGISTER.md), [R-20](../risks/REGISTER.md)
- Phase: 01.2 (memory init), 02.x (persistent memory), 03.4 (PARA + rituals)
- Related ADRs: ADR-003 (Pydantic-AI), ADR-014 (security), ADR-019 (vertical-rituals)
