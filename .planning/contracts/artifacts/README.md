# Bounded Context: `artifacts`

> **Status:** IMPLEMENTED (Phase 01.5, Wave 1 — ADR-038 envelope model).
> Implementation: `backend/src/artifacts/` + `backend/migrations/versions/artifacts/0001_artifacts_core.py`.

## Purpose

The `artifacts` context owns **persistent storage of work products** generated within cells:

- **Artifact envelopes** — typed (`document` / `code` / `asset`), addressable, taggable objects with an append-only immutable version history and a `current_version_num` head pointer.
- **Yjs documents** — CRDT-backed content (bytea state + state vector, merged with pycrdt). Wave 1 persistence is **REST-only** (synchronous merge under `FOR UPDATE` ⇒ read-your-writes); the y-websocket sync server is deferred (RQ-20260701-001) and will reuse the same `state`/`state_vector`/update-log without schema change.
- **S3 binary assets** — blobs in S3-compatible object storage (MinIO dev / Yandex Object Storage prod) with a Postgres lifecycle row per object (`pending → stored → deleted`).
- **Citeable `artifact://` URLs** — `artifact://<cell_id>/<artifact_id>[/v<N>]`, stable forever (immutable versions + write-once S3 keys + no-UPDATE DB grants).

This context separates *what* an artifact is (a typed, addressable persistent object) from *how* it was produced (the `tasks` and `agents` contexts).

## Ubiquitous Language

| Term                | Meaning                                                                                                    |
|---------------------|------------------------------------------------------------------------------------------------------------|
| **Envelope**        | The `artifacts.artifacts` row: type, title, tags, owner, head pointer, soft-delete flag.                    |
| **Version**         | An append-only immutable `artifact_versions` row (`UNIQUE(artifact_id, version_num)`), XOR one of: inline jsonb / S3 object / Yjs snapshot. |
| **Head**            | `current_version_num` on the envelope — what a version-less `artifact://` URL resolves to (0 = nothing committed → 404). |
| **Yjs Document**    | The live CRDT head (`state` bytea + `state_vector`), one per envelope, merged synchronously under a row lock. |
| **Update Log**      | `yjs_updates` append log (seq IDENTITY) — pruned by compaction, never authoritative for state.              |
| **Snapshot**        | Immutable point-in-time Yjs state (`yjs_snapshots`) — created by explicit commit or compaction; never deleted. |
| **Compaction**      | update_count > 500 OR state > 1 MiB ⇒ snapshot the head + prune the log + reset the counter.                |
| **Key Reservation** | Presign inserts a `pending` `s3_objects` row; `UNIQUE(bucket, s3_key)` rejects a duplicate at reserve time. |
| **Content Hash**    | SHA-256 computed **server-side** at upload complete (client input is never trusted).                        |
| **Storage Usage**   | `cell_storage_usage.bytes_total` — transactional per-cell accounting (enforcement deferred, RQ-20260701-002). |

## Invariants

- Every row in all 7 tables is scoped to exactly one `cell_id`; **FORCE RLS** with the direct predicate `cell_id = _shared.current_cell_id()` (USING + WITH CHECK) — missing GUC ⇒ default-deny.
- `cell_id` is denormalized onto every child table and pinned by **composite anti-drift FKs** `(parent_id, cell_id) → parent(id, cell_id)` — a child can never claim a different cell than its parent.
- `artifact_versions` and `yjs_snapshots` are **immutable at the DB privilege level**: `oriion_app` has no UPDATE and no DELETE on them. `artifact://.../vN` therefore never changes meaning.
- Version numbering is serialized by a `FOR UPDATE` lock on the envelope; `UNIQUE(artifact_id, version_num)` remains authoritative and a direct-SQL racer triggers a re-read-and-retry (max 3 attempts → 409).
- The version storage XOR: exactly one of `content_inline` / `s3_object_id` / `yjs_snapshot_id` is set, matching `storage_kind` (`CHECK` constraint). `storage_kind` is the evolution seam: Wave-2 `'connector'` / Wave-3 `'gitea_ref'` land as a CHECK-swap, no backfill.
- `s3_objects.(bucket, s3_key)` is globally unique; keys follow `<env>/<cell_id>/<artifact_id>/<version_num>/<filename>` (ADR-012) with a strict filename charset (path-traversal guard).
- `content_hash_sha256` / `byte_size` are computed server-side after upload completes; the bucket is never public (presigned POST 5-min TTL for upload, signed GET 1-hour TTL for download).
- Envelope deletion is **soft** (`deleted_at`): versions stay, `s3_objects` rows flip to `deleted` (physical removal = janitor), logical bytes are freed from `cell_storage_usage`.
- Resolver: malformed URL → 422; cell mismatch → the **same 404** as not-found (no cross-cell existence oracle).
- Compaction preserves the latest state + state vector and every snapshot — only `yjs_updates` rows are pruned.
- `cell_storage_usage.bytes_total` changes in the same transaction as the version/upload/delete that caused it.

## Cross-Context Dependencies

- **multitenancy** — every row is scoped to `cell_id` (FK to `multitenancy.cells`, RLS via the shared 3-GUC model).
- **tasks** — `tasks.task_artifacts.s3_key` / `.yjs_document_id` (dangling text/uuid columns, unchanged in this phase) resolve against `artifacts.s3_objects.s3_key` / `artifacts.yjs_documents.id` — queryable targets, no FK.
- **iam** — `owner_user_id` / `created_by_user_id` reference the authenticated principal; the API is JWT-authenticated and the tenant context derives the cell.
- **agents** — `created_by_agent_id` marks agent-produced artifacts (orchestrator hot-path wiring is a follow-up phase, mirror of 01.4→01.4b).
- **billing** — storage quota **enforcement** per ADR-012 tariffs consumes `cell_storage_usage` (deferred, RQ-20260701-002).

## API & Events

- REST surface: `api.yaml` (mounted under `/api/v1`, errors = RFC-7807 problem+json with machine `code`).
- CloudEvents: `events.yaml` — 5 events emitted via the house `src/_shared/cloudevents.py` mechanism (structlog transport now, Redis Streams later without call-site changes).

## ADR References

- **ADR-012** — Артефакты: Yjs для документов, S3 для ассетов (parent decision).
- **ADR-038** — Envelope-схема в едином `artifacts` schema (judge-panel composite; binding design for this contract).
- **ADR-024** — Bounded Context Contracts (this contract's format + 1:1 conformance rule).
- **ADR-009** — RLS / 3-GUC tenant model.

## Deferred (tracked)

- y-websocket real-time co-editing — RQ-20260701-001 (schema-ready: state + state_vector + update log).
- Storage quota enforcement by tariff — RQ-20260701-002 (`cell_storage_usage` accounting is live).
- FTS / pgvector search — `text_export` + jsonb `tags` reserve the space without backfill.
- Connector-mode (Wave 2) / Gitea refs (Wave 3) — `storage_kind` CHECK-swap.
- Scheduled janitor for stale `pending` reservations and physical S3 deletion (service method `purge_stale_pending` exists; scheduling is a follow-up).
