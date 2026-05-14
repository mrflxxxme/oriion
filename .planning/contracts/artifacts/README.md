<!-- SKELETON — Wave 1 deliverable (per ADR-024). Draft quality README; SQL/YAML files are placeholders. -->

# Bounded Context: `artifacts`

> **Status:** SKELETON (Wave 1 deliverable per ADR-024). Real DDL/API/events land in Milestone D, Wave 1 phase.

## Purpose

The `artifacts` context owns **persistent storage of work products** generated within cells:

- **Y.js collaborative documents** — CRDT-backed structured content (notes, canvases, agent scratchpads) that support real-time co-editing across users and agents.
- **S3 binary assets** — arbitrary blobs (images, attachments, generated files) stored in S3-compatible object storage, with metadata tracked in Postgres.

This context separates *what* an artifact is (a typed, addressable persistent object) from *how* it was produced (the `tasks` and `agents` contexts).

## Ubiquitous Language

| Term             | Meaning                                                                                              |
|------------------|------------------------------------------------------------------------------------------------------|
| **Y.js Document**| A CRDT-backed structured document (rich text, tree, map). Supports concurrent edits without locking. |
| **Snapshot**     | A point-in-time persisted state of a Y.js document (for compaction + history).                       |
| **State Vector** | Y.js construct describing what updates a client has seen; used for diff sync.                        |
| **S3 Asset**     | A binary blob in S3-compatible storage, identified by `(bucket, key)` with metadata in Postgres.     |
| **Content Hash** | SHA-256 of asset body; used for dedup and integrity verification.                                    |
| **Visibility**   | Access scope of an asset: `cell-private` / `organization` / `public-link`.                           |

## Invariants (placeholder — TODO in Milestone D, Wave 1)

- TODO: every artifact is scoped to exactly one `cell_id`; cross-cell access goes through RBAC, not direct refs.
- TODO: Y.js document state evolves monotonically — older snapshots remain readable for history.
- TODO: `s3_assets.(s3_bucket, s3_key)` is globally unique.
- TODO: `content_hash_sha256` is computed server-side after upload completes; never trusted from client.
- TODO: deleting an asset record requires the underlying S3 object also be deleted (no orphans).
- TODO: Y.js document compaction preserves the latest state vector — no data loss across compactions.

## Cross-Context Dependencies

- **multitenancy** — every artifact is scoped to `cell_id` (which transitively gives `organization_id`).
- **tasks** — `tasks.task_artifacts` rows reference `yjs_documents.id` or `s3_assets.id` for task outputs.
- **rbac** — per-cell access control gates read/write to artifacts.
- **iam** — `last_editor_user_id` references the authenticated principal (Wave 1+).
- **agents** — agent executions produce artifacts (output side of the task lifecycle).

## Why Wave 1 (not Wave 0)

Y.js infrastructure is **non-trivial** — it requires:

1. A real-time sync layer (WebSocket-based provider).
2. CRDT merge semantics across browser + backend.
3. Snapshot/compaction strategy to bound document size.
4. Tooling for diff inspection + rollback.

For **Wave 0**, structured content lives **inline as JSONB** in `tasks.task_outputs` (or similar).
This is acceptable for single-author, single-session workflows.
Real-time co-editing is a Wave 1 differentiator and lands here.

S3 asset storage is also scheduled for Wave 1 — Wave 0 can rely on inline base64 or local fs for
the small set of demo artifacts.

## ADR References

- **ADR-024** — Bounded Context Contracts (this context schema, §1).
- TODO: future ADR for Y.js provider choice (Hocuspocus vs custom WebSocket vs SaaS).
- TODO: future ADR for S3-compatible storage backend (MinIO self-hosted vs cloud vendor).

## Open Questions (defer to Milestone D, Wave 1)

- Snapshot frequency policy: time-based vs operation-count-based vs hybrid.
- Y.js document size limits and compaction threshold.
- Asset lifecycle: TTL for ephemeral artifacts, cold-storage tier for old assets.
- Per-asset signed URL expiry policy.
- Garbage collection of orphaned S3 objects (artifacts that lost their parent task).
- Conflict resolution UX when two agents Y.js-edit the same document simultaneously.
