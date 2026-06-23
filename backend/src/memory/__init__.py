"""Memory bounded context (ADR-011 Wave-1).

Two-level manual-control memory:

- **cell memory** (``memory.memory_entries``) — shared cell knowledge base,
  RAG-recallable by any agent in the cell.
- **role memory** (``memory.role_memory_entries``) — per agent-instance
  personal memory (preferences, style/process), scoped additionally by
  ``agent_id``.

Plus conversation history (FIFO + summarize-on-overflow) and a filter-agent
that extracts memories after a task completes. Single ``memory`` schema with
``cell_id`` + FORCE-RLS (grill 2026-06-23, Q3); 256-dim YandexGPT embeddings
behind an injectable embedder port (Q1).
"""
