# ADR-038: Artifacts — envelope-схема в едином `artifacts` schema (composite judge-panel design)

- **Status:** Accepted (autonomous, ADR-037 D4/D5 — judge-panel verdict; founder post-hoc audit via DECISIONS-LOG)
- **Date:** 2026-07-02
- **Deciders:** Autonomous runner (judge-panel N=3 + evaluator, session `charming-kepler-c814fe`), per ADR-037

## Context

Phase 01.5 реализует ADR-012 (Yjs-документы + S3-ассеты + citeable `artifact://` URLs). Два источника расходились: implementation-sketch ADR-012 описывает **envelope**-модель (`artifacts.artifacts` + `artifacts.versions` + `collaboration.yjs_docs`), а contract-skeleton (`.planning/contracts/artifacts/schema.sql`) — **плоскую** модель (`yjs_documents` + `s3_assets`, jsonb-snapshot placeholder). Выбор схемы — wide fork с высоким blast radius (schema + `artifact://` семантика версий), решён через judge-panel (ADR-037 D5): 3 независимых генератора (ADR-faithful / minimal-flat / evolution-optimal) + evaluator по лексикографической рубрике (correctness → security → simplicity → cost → perf).

Constraints: `tasks.task_artifacts` уже существует (storage_kind XOR `inline|s3|yjs_document`, висячие `s3_key`/`yjs_document_id`) и НЕ меняется; FORCE-RLS house-паттерн `_shared.current_cell_id()`; REST-only Wave 1 (y-websocket эскалирован отдельно, RQ-20260701-001); квоты по тарифам — только учёт байт (RQ-20260701-002); ADR-024 фиксирует 10 bounded contexts — нового `collaboration` context не будет.

## Decision

**Envelope-модель в едином Postgres schema `artifacts`** (миграционная ветка `artifacts_0001`, greenfield), победитель G1 + 6 grafts из проигравших дизайнов:

| Таблица | Роль |
|---|---|
| `artifacts.artifacts` | envelope: `id`, `cell_id`, `artifact_type CHECK ('document','code','asset')`, `title`, `tags jsonb`, `owner_user_id`, `created_by_agent_id`, **`current_version_num int NOT NULL DEFAULT 0`** (graft G3 — без циклического FK), `deleted_at` (soft-delete) |
| `artifacts.artifact_versions` | append-only, immutable (GRANT без UPDATE): `UNIQUE(artifact_id, version_num)`, `storage_kind CHECK ('inline','s3','yjs_snapshot')` + XOR (`content_inline jsonb` \| `s3_object_id FK` \| `yjs_snapshot_id FK`), `byte_size`, `content_hash_sha256`, **`text_export text NULL`** (graft G2 — hook для будущего FTS/vector без backfill) |
| `artifacts.yjs_documents` | живая CRDT-голова; **target для `tasks.task_artifacts.yjs_document_id`**; `artifact_id UNIQUE FK`, `state bytea`, `state_vector bytea`, `update_count`, `last_compacted_at` |
| `artifacts.yjs_updates` | append-лог (`seq bigint IDENTITY`), прунится компакцией |
| `artifacts.yjs_snapshots` | immutable snapshot-история; referenced из `artifact_versions.yjs_snapshot_id` |
| `artifacts.s3_objects` | (graft G3) lifecycle-таблица: `UNIQUE(bucket, s3_key)`, `status CHECK ('pending','stored','deleted')`; **target для `tasks.task_artifacts.s3_key`**; presign вставляет `pending`-строку → **транзакционная резервация ключа** (лечит presign-race G1) |
| `artifacts.cell_storage_usage` | `cell_id PK`, `bytes_total` — учёт для отложенного quota-enforcement |

Ключевые механики:
- **Yjs: bytea + pycrdt, синхронный merge.** REST-запись: `FOR UPDATE` на yjs_documents → append в yjs_updates → pycrdt-merge в `state` + refresh `state_vector` → commit (read-your-writes гарантирован). Компакция = прунинг лога старше свежайшего snapshot при `update_count > 500` или > 1 MiB. Версия = явный commit: state → `yjs_snapshots` + `artifact_versions(storage_kind='yjs_snapshot')`.
- **RLS:** FORCE ROW LEVEL SECURITY на всех таблицах, прямой предикат `cell_id = _shared.current_cell_id()` USING+WITH CHECK; `cell_id` денормализован на детей + **composite anti-drift FK** `(parent_id, cell_id) → parent(id, cell_id)` при `UNIQUE(id, cell_id)` на родителе (graft G2).
- **`artifact://<cell_id>/<artifact_id>[/v<N>]`:** строгий regex; cell-mismatch → **404** (graft G2 — без existence-oracle); без версии → head через `current_version_num`; `/vN` → immutable `artifact_versions` строка.
- **S3:** presigned POST (5-мин TTL) → клиент грузит → `complete`: сервер HEAD'ит объект, считает sha256/byte_size server-side (клиенту не доверяем), `pending→stored`, создаёт version-строку. Signed GET 1h TTL. Janitor для протухших `pending` и failed-delete.
- **Evolution (graft G3):** Wave-2 `'connector'` / Wave-3 `'gitea_ref'` = CHECK-swap на `storage_kind`, без backfill; y-websocket (Wave 2+/по ack) переиспользует `state`+`state_vector`+updates-лог без изменения схемы.

## Consequences

- ✅ `artifact://` версии стабильны навсегда (immutable versions + write-once S3 keys + no-UPDATE grants на уровне БД).
- ✅ `tasks.task_artifacts` не тронут; обе висячие ссылки получают queryable targets.
- ✅ Contract-skeleton (`.planning/contracts/artifacts/*`) переписывается под envelope в этом же PR (single source of truth, P-INIT-2).
- ⚠️ 7 таблиц против 2 в скелете — цена envelope; заплачена один раз, до появления данных.
- ⚠️ Row-lock сериализует записи в один Yjs-док — известный REST-only bottleneck, снимается будущим sync-сервером.
- 🔮 FTS/vector-поиск: `text_export` + jsonb `tags` дают место для GIN/pgvector индексов без data-backfill.

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| G2: flat + per-type version children (contract-skeleton) | Наименьшая поверхность (5 таблиц); сильнейший RLS-anti-drift | `artifact://` grammar поверх ДВУХ ID-namespace с вероятностной дизъюнктностью; `tags[]`/unified type/`'code'` из ADR-012 без места в схеме; Wave-2 registry = identity-backfill под данными | Correctness-гейт: слабое прочтение ADR-012 grammar; отложенная цена в худшей фазе. Grafts (anti-drift FK, text_export, 404) забраны |
| G3: envelope + async-merge update-log | Lock-free запись; Wave-4 y-redis контракт готов | Нарушает read-your-writes (200 на POST, потом stale GET; `/vN` может не содержать только что сделанных правок); компакция-worker — чистый Wave-1 overhead | Correctness-гейт: починка = синхронный merge = G1. Grafts (current_version_num, s3_objects) забраны |
| jsonb snapshot (skeleton placeholder) | Нет нового формата | Лосси для CRDT-метаданных, не мержится, сам помечен TODO-replace | Отклонено всеми тремя генераторами независимо |

## Links

- Risk: [R-05](../risks/REGISTER.md) (data leak — RLS), [R-07](../risks/REGISTER.md)
- Phase: [01.5-artifacts](../roadmap/wave-1-core-mvp/phases/01.5-artifacts.md)
- Related ADRs: ADR-012 (артефакты — базовое решение), ADR-024 (bounded contexts), ADR-037 (autonomy: judge-panel протокол)
- Panel evidence: `evidence/judge_panel_artifacts_schema.json` (в PR), полные submissions — session scratchpad
- Escalations: RQ-20260701-001 (co-editing scope), RQ-20260701-002 (storage quotas)
