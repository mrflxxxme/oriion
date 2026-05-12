# ADR-012: Артефакты — Yjs для документов, S3 для ассетов

- **Status:** Accepted

## Decision

### Гибрид по типу артефакта

| Тип | Хранилище | Версионирование | Co-editing |
|---|---|---|---|
| Документы (markdown, html, текст) | Yjs CRDT + Postgres for persistence | История изменений в Yjs | Real-time (y-websocket) |
| Код | Файлы-артефакты + Yjs-история на MVP, Gitea per workspace в Wave 3+ | Git-like diff | Через UI diff-view |
| Ассеты (изображения, видео, PDF, бинарники) | S3 (Yandex Object Storage), immutable + теги | Новая версия = новый объект | — |

### Citeable URL

`artifact://<cell_id>/<artifact_id>[/v<version>]` — стабильный идентификатор. Агент в новой задаче может ссылаться.

### Поиск

- Full-text (Postgres GIN / Tantivy)
- Векторный (pgvector — embedding(title+excerpt))
- Фасеты (роль-автор, тип, дата, теги, проект)

### Опция connector-режим (Wave 2+)

Артефакт «живёт» в Яндекс.Диске / Google Drive клиента, в нашей системе — ссылка + метаданные. Реализуется через connector framework.

### Лимиты по тарифу

| Тариф | Storage |
|---|---|
| Trial | 1 ГБ |
| Solo | 5 ГБ |
| Команда 5 | 10 ГБ |
| Команда 15 | 50 ГБ |
| Команда 30 | 200 ГБ |
| Enterprise | Custom |

## Implementation

```
artifacts.artifacts
  id, cell_id, type, title, owner_user_id, 
  created_by_agent_id?, tags[], current_version_id

artifacts.versions
  id, artifact_id, version_num, created_at, author,
  content_ref (yjs_doc_id или s3_key), metadata

collaboration.yjs_docs  (Wave 1+)
  doc_id, cell_id, snapshot_bytea, last_snapshot_at
```

### Storage paths

- S3 bucket structure: `<env>/<cell_id>/<artifact_id>/<version_num>/<filename>`
- Pre-signed URLs для upload (POST policy с 5-мин TTL)
- Server-side encryption включён
- Asset URL отдаётся через signed-link с TTL 1 час (не публичный bucket)

### Yjs gaarantees

- Eventually-consistent, не транзакционный
- Single-node y-websocket до Wave 4 → limit ~500 одновременных редакторов на доке
- Wave 4+: y-redis для кластеризации

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-07](../risks/REGISTER.md)
- Phase: 01.3 (artifacts initial), 02.x (asset tagging), 03.x (Gitea), 04.x (y-redis)
- Related ADRs: ADR-011 (memory ↔ artifacts)
