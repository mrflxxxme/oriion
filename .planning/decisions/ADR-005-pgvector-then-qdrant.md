# ADR-005: pgvector на старте, Qdrant standalone в Wave 4

- **Status:** Accepted (amendment 2026-05-19, see «Wave 0 vector schema decisions»)

## Wave 0 vector schema decisions (2026-05-19)

> Adopted in the pre-Phase-00.3 contract extension (Phase 00.3 + 00.4 combined PR).

1. **Baseline dim: `vector(1024)`** per `cell_<uuid>.memory_entries.embedding`. Matches GigaChat embeddings native + leaves headroom for OpenAI 1536-truncate via BYOK.
2. **Provenance columns.** `memory_entries` carries three audit columns:
    - `embedding_provider text NOT NULL` — e.g. `yandex`, `gigachat`, `openai-byok`, `local`.
    - `embedding_model text NOT NULL` — e.g. `text-search-doc`, `GigaChat-Embeddings`.
    - `embedding_dim int NOT NULL CHECK (embedding_dim <= 1024)` — native dim before truncate/pad.
    Provider-canonicalization migration deferred to Wave 1.
3. **Truncate/pad strategy.** Yandex 256-dim embeddings pad zeros to 1024 before storage; OpenAI 1536-dim truncate to 1024 (last 512 dims dropped — acceptable for cosine sim with token loss <3% per OpenAI dim-reduction guidance). HNSW index built on the 1024-dim canonical vector.
4. **HNSW params:** `(m=16, ef_construction=64)` — baseline per pgvector docs; tune Wave 1+ based on query patterns.



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
