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

## Wave-1 implementation status (Phase 01.4, 2026-06-23)

Implemented in Phase 01.4 (session `dazzling-shamir-c26b51`), with two grounded
amendments to this ADR:

- **Embedding model — YandexGPT 256-dim, not 1024 (grill Q1).** Yandex text
  embeddings (`text-search-doc` / `text-search-query`) are **256-dim**; the
  "1024-dim YandexGPT" above was wrong. GigaChat embeddings are currently
  `NotImplementedError`. The dimension is a single source of truth
  (`src.memory.models.MEMORY_EMBEDDING_DIM = 256`); the embedder is asymmetric
  (doc model for stored entries, query model for searches) behind an injectable
  port. Changing the dim later = re-embed + reindex migration.
- **Storage — single `memory` schema + `cell_id` + RLS, not per-cell schemas
  (grill Q3).** `memory.memory_entries` / `memory.role_memory_entries` /
  `memory.conversation_history` are FORCE-RLS via `_shared.current_cell_id()`
  (mirrors billing/iam/tasks), with HNSW `vector_cosine_ops`. This
  **supersedes** the unused 1024-dim per-cell `cell_<uuid>.memory_entries`
  placeholder created by `multitenancy/0004_provision_cell_schema_function`
  (divergent + unused → cleanup chip).

**Delivered:** cell memory + role memory (store/search/CRUD API, RLS,
embed-on-store, advisory soft caps 500/cell·200/role) + conversation history
(FIFO N=50 + summarize-on-overflow **seam**) + the manual «запомни» trigger.
Conversation summaries are stored as `memory_entries` with
`kind='conversation_summary'` (as specified above).

**Implemented in `01.4b — memory auto-extraction`** (2026-06-24,
`tender-clarke-a1cd06`): the **automatic** filter-agent (lite-LLM extraction after
each *succeeded* task) + the **LLM conversation summarizer** + their orchestrator/
worker post-task wiring. Decisions: the `task_steps` rows are billed under a new
horizontal **`memory_curator`** archetype with `role_category='analyzer'` (reuse —
no CHECK migration) and `step_type='llm_call'` (the step CHECK has no
`memory_extraction` value; `phase` lives in `input_jsonb`); the orchestrator gets a
`memory_extraction` seam (mirror of `quota_admission`: default `None ⇒ no-op`, the
worker wires the real hook) that runs on success **pre-final-write** so the cost
folds into the per-task cap + step-sum (`total == SUM(steps)`, never rejecting). The
**conversation-turn producer** (capturing agent-turns into `conversation_history`
*during* a task) is **deferred to a future per-agent chat phase (decision 2026-07-01)**:
there is no multi-turn conversation surface yet (tasks are single-shot; no chat endpoint),
and `conversation_history` is per *single* agent, so team-task turns have no unambiguous
`agent_id` — team work is already fully recorded in `tasks`/`task_steps`/`task_artifacts`.
The storage + summarizer scaffold is ready (the 01.4 grill pulled it forward from this
ADR's original Wave-2 scope); in 01.4b the summarizer is wired + tested via direct `append()`.
Live-validated in-process vs DeepSeek (`scripts/live_golden_memory.py` 5/5); the
Dramatiq+Redis worker transport stays proven on Linux. See
[`phases/01.4b-memory-auto-extraction.md`](../roadmap/wave-1-core-mvp/phases/01.4b-memory-auto-extraction.md).

**Deferred (later waves, per this ADR):** RAG-inject into agent prompts (grill
Q4), the «Что помнит [агент]» view/edit/delete UI panel (grill Q6 → `01.4-ui`),
the 90-day conversation-history retention sweep + >1yr auto-archive, and Wave-2
persistent-across-sessions / Wave-3 PARA «Знания команды».

Phase doc: [`phases/01.4-memory.md`](../roadmap/wave-1-core-mvp/phases/01.4-memory.md).

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-19](../risks/REGISTER.md), [R-20](../risks/REGISTER.md)
- Phase: 01.2 (memory init), 02.x (persistent memory), 03.4 (PARA + rituals)
- Related ADRs: ADR-003 (Pydantic-AI), ADR-014 (security), ADR-019 (vertical-rituals)
