# ADR-009: Multitenancy — Cell как domain-first concept + 3 уровня изоляции

- **Status:** Accepted

## Decision

### Cell как first-class domain concept (Wave 0)

```
Workspace (1 user owns N workspaces по тарифу)
  └── Cell (= AI team, dedicated isolation)
       ├── cell_id (UUID)
       ├── region (Wave 0: только 'ru-central-1')
       ├── status (provisioning / active / paused / archived)
       ├── created_at, updated_at
       ├── plan_tier (linked to subscription)
       ├── llm_config (per cell — choice of stack/byok)
       ├── stack_preference ('default' / 'ru-only' / 'byok-only' / 'premium-western')
       └── secrets_ref (Lockbox path)
```

**Каждая cell имеет:**
- Свой `cell_id` namespace во ВСЕХ multi-tenant таблицах
- Свои secrets в Lockbox (отдельный path)
- Свой sandbox-context (per-task gVisor / Pyodide isolation)
- Свой webhook-endpoint (для outbound events)
- Свой credit balance (учёт в `billing.credit_transactions`)
- Свой audit-stream (filtered by cell_id)
- Свой scoped service account для backend

### Уровни изоляции

| Уровень | Когда | Что изолировано |
|---|---|---|
| **B+ (логический cell)** | Wave 0+ default | Postgres schema/RLS by cell_id; Pyodide WASM client-side; per-cell Lockbox path; per-cell network whitelist |
| **C (dedicated namespace)** | Wave 3+ опция Pro-tariff | + k8s namespace per Pro-cell; dedicated runtime pods; dedicated sandbox VM-pool (gVisor); separate Redis instance |
| **D (dedicated cluster)** | Wave 5+ Enterprise / on-premise | + полный k8s cluster или customer's VPC; on-premise Helm chart; dedicated DB instance; BYOK для всех credentials (S3, KMS) |

### Wave 0 B+ (логический cell) details

#### Postgres isolation
- **schema-per-cell** для критичных bounded contexts: `cell_<uuid>` schemas для `runtime`, `artifacts`, `memory`
- **RLS-pinned** для shared таблиц: `iam.workspaces`, `iam.cells`, `iam.cell_members`, `billing.*`
- App-user → `SET LOCAL app.current_cell_id = '<uuid>'` per request (FastAPI dependency)
- FORCE ROW LEVEL SECURITY включён, exceptions только через superuser

#### Sandbox isolation
- **Pyodide WASM** — runs in client browser (R-05 mitigated)
- **MCP-серверы** — separate processes/containers, scoped credentials per cell

#### Network whitelist
- Per-cell config: whitelisted external endpoints (Bitrix24 / 1С / WB endpoints)
- Network egress filter в backend (http client respects per-cell allowlist)
- Wave 3+: physical network policies в k8s

#### Audit
- `audit.audit_log` partitioned by cell_id для быстрых per-cell queries
- Retention 3 года (ФЗ-152)
- Cell-deletion НЕ удаляет audit history до retention expiry

### Region (Wave 0 single, Wave 4 multi)

**Wave 0-3:** только **`ru-central-1`** (Yandex Cloud Moscow):
- ФЗ-152 compliance: все ПДн в РФ
- Marketing: «Ваши данные — в России»

**Wave 4+:** optional regions:
- `ru-central-2` (Yandex Cloud SPb) — для disaster-recovery
- `kz-1` (Yandex Cloud Almaty) — для СНГ expansion
- Customer's own VPC — для Enterprise on-premise

**Region locked при cell provisioning** — миграция через support ticket only.

### Cell provisioning workflow

```
User upgrades from trial → paid tariff
  ↓
ЮKassa webhook → billing-service
  ↓
billing.subscription активируется
  ↓
cell-provisioner spawns:
  1. Создаёт Cell entity в БД
  2. Применяет Postgres migrations для cell_<uuid> schemas
  3. Создаёт Lockbox path для secrets
  4. Привязывает к billing.subscription
  5. Activates default team-preset (если был указан в onboarding wizard)
  6. Status → 'active'
  ↓
User redirected → /cell/<uuid>/onboarding
```

**Provisioning time target:** <30 секунд.

### Trial-cells (Wave 1)

Trial workspace = lightweight cell:
- 500 кредитов pre-loaded
- 14 дней TTL
- Auto-cleanup orphaned trials (R-26 mitigation)
- При conversion в paid — trial-cell мигрирует в full cell

## ФЗ-152 compliance с дня 1

- Все ПДн-таблицы в РФ-зоне (Yandex Cloud ru-central-1)
- Уведомление РКН оператора ПДн (Phase 00.2 blocker, OQ-04)
- Audit-журнал доступа к ПДн с retention 3 года
- Трансграничная передача (Wave 2+ Western LLM-стек) — только при явном consent
- Без consent — forcibly RU-only cell.stack_preference

## Marketing copy (cell-based)

- «Каждая ваша AI-команда работает в собственной изолированной "ячейке"»
- «Данные команды — в России, в собственном защищённом контуре»

## Migration roadmap

| Wave | Что |
|---|---|
| W0 | Cell as domain concept, schema-per-cell для runtime/artifacts/memory, RLS, single region ru-central-1 |
| W2 | Cell provisioning workflow + trial-cells lifecycle |
| W3 | Optional physical-cell upgrade для Pro: dedicated k8s namespace + dedicated VM-sandbox |
| W4 | Migration tool существующих B+ cells → C-level (offline window 1-2 часа per cell) |
| W5+ | On-premise Helm chart для D-level Enterprise + multi-region |

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-08](../risks/REGISTER.md)
- Phase: 00.3 (DB+RLS+cell schema), 04.4 (physical-cell upgrade)
- Related ADRs: ADR-014 (security), ADR-008 (billing per cell)
