# ADR-005: pgvector на старте, Qdrant standalone в Wave 4

- **Status:** Accepted

## Decision

**Wave 0-3:** **pgvector** — extension в основной PostgreSQL.

**Wave 4+:** Миграция на **Qdrant** как standalone-сервис при росте >5M векторов или просадке `vector_search_p95_latency > 500ms`.

**Embedding-провайдер:** YandexGPT Embeddings (managed) на MVP. Wave 5+ — self-hosted bge-m3 / multilingual-e5-large на GPU.

## Implementation

### Wave 0-3 (pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE cell_<uuid>.memory_entries (
    id uuid PRIMARY KEY,
    content TEXT,
    embedding vector(1024),  -- YandexGPT Embeddings dim
    metadata JSONB,
    created_at timestamptz
);

CREATE INDEX ON cell_<uuid>.memory_entries USING hnsw (embedding vector_cosine_ops);
```

### Wave 4 migration trigger

- vector_search_p95_latency > 500ms (sustained 1 week)
- > 5M активных векторов
- Появление customer demand на advanced features (filtered search, multi-tenant collections)

### Wave 4 architecture (Qdrant)

- One Qdrant collection per workspace (или один с фильтром — bench-test)
- Payload: workspace_id, agent_id, level (workspace/role), source_id, metadata
- Dual-write миграция: новые embeddings → pgvector + Qdrant; backfill истории chunked job

## Consequences

- Один сервис меньше на MVP
- JOIN с реляционными таблицами нативно
- RLS работает в той же транзакции

## Monitoring (Wave 0+)

- Метрика `vector_search_p95_latency` per workspace
- Алерт при >300ms (warning), >500ms (critical → trigger Wave 4 migration planning)

## Links

- Phase: 00.3 (Postgres + pgvector setup), 04.2 (Qdrant migration)
- Stack: [_meta/stack.md](../_meta/stack.md) → Vector
