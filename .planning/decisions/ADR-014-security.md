# ADR-014: Security — RBAC + DLP + изоляция memory от tool-output + операционная гигиена

- **Status:** Accepted (amendments 2026-05-19, see «Wave 0 security decisions»)

## Wave 0 security decisions (2026-05-19)

> Adopted in the pre-Phase-00.3 contract extension (Phase 00.3 + 00.4 combined PR).

1. **3-GUC default-deny RLS posture.** Per ADR-009 amendment 2026-05-19: `app.current_user_id` + `app.current_workspace_id` + `app.current_cell_id` set per transaction via FastAPI dependency `get_tenant_db_session`. Missing GUC → `NULL` → policy evaluates FALSE → zero rows visible. Integration tests assert default-deny (`tests/multitenancy/test_rls_isolation.py`).
2. **KMSProvider Protocol — Wave 0 → Wave 1 migration path:**
    - **Wave 0:** `LocalAESKMS` impl. AES-256-GCM with master key from env `BYOK_MASTER_KEY_B64` (32-byte base64). DEK envelope wrap done in-process. NOT production-grade — dev/test only.
    - **Phase 00.6+:** `YandexKMS` impl. Real envelope encryption via Yandex KMS API (`TBD_YANDEX_CLOUD_KMS_KEY_ID`). DEK wrapped by Yandex KMS master key, never exits HSM.
    - DI selection via env `KMS_BACKEND=local|yandex` (default `local`).
    - BYOK keys never logged in plaintext — only `key_fingerprint` (sha256[:8]) surfaced in responses.
3. **Audit log append-only enforcement.** `audit.audit_log` UPDATE/DELETE blocked by trigger raising exception. Partitioned by month with `default` catch-all partition (Wave 0; pg_partman Wave 1+). 3-year retention per FZ-152.
4. **CloudEvents — log-only Wave 0.** All domain events emitted via structlog `cloudevent=True` tag (matches Phase 00.2 pattern); Wave 1+ swap to Redis Streams `XADD` keeps emit API stable.



## Decision

Многослойная защита:

### 1. RBAC per workspace
- **Owner** (1): биллинг, передача владения, всё
- **Admin** (0..N): подключение коннекторов, управление ролями, audit log
- **Member** (0..N): ставит задачи, видит общие артефакты
- **Viewer** (0..N): read-only
- **Bot/Service** (для API): scope-токены
- Granularity: whitelist агентов per-user, visibility артефактов, approval-rights

### 2. Input/Output фильтрация (Prompt Injection защита)
- На входе любого external-контента (email/web/file) — классификатор инъекций (Prompt Guard / собственный на bge)
- На выходе — DLP-классификатор: ПДн (ФИО+ДР, паспорт, СНИЛС, ИНН ФЛ), банковские, медицинские, ком.тайна (whitelist клиента)
- Действие при срабатывании: блокировка с эскалацией («Подтвердить отправку?») / маскирование

### 3. Capability sandboxing
- «Опасные» tools (`send_email`, `send_telegram`, `transfer_money`, `commit_to_prod_branch`, и т.д.) требуют human approval
- Список «опасных» — конфигурируется владельцем workspace
- High-stakes роли (Юрист/Accountant/Dev) → `requires_human_approval: true` глобально

### 4. Изоляция memory от tool-output
- Tool-output по умолчанию НЕ сохраняется в memory
- Только через filter-agent или явный consent пользователя
- См. [ADR-011](./ADR-011-memory-2-level.md)

### 5. Cost защита (runaway)
- 3-уровневые лимиты: per-task / per-agent-day / per-cell-month
- Hard kill-switch при превышении
- Алерты в email + Telegram
- Deadman switch для autonomous-режима

### 6. Cross-tenant изоляция
- RLS в Postgres по `cell_id`
- Отдельные коллекции pgvector/Qdrant
- Pyodide WASM client-side / gVisor sandbox per-execution
- Сетевая whitelist из sandbox (только tenant-config endpoints)
- Запрет cross-cell tool-calls в runtime

### 7. Операционная гигиена (наша команда)
- **Zero standing access** в prod
- **JIT-доступ** через тикет: запрос → одобрение второго инженера → токен на 4ч → автоотзыв → лог сессии (Teleport / собственный bastion)
- **Шифрование backup** (envelope + Yandex KMS), отдельный bucket с access-policy
- **Audit ПДн-доступа**: все SELECT по таблицам с ПДн логируются, retention 3 года, алерт на массовую выборку
- **2FA** обязательно для Owner/Admin
- **Onboarding/offboarding**: чек-лист отзыва доступов 24ч, pre-employment screening для prod-доступа
- **Security training** раз в 6 мес

### 8. Reporting & DR
- Immutable append-only audit log (3-year retention)
- Опция «Approval mode» на роль
- Регулярный security scan MCP-инвентаря
- 72-часовое уведомление РКН + клиенту при утечке ПДн
- IR-регламент: триаж 1ч → containment 4ч → eradication 24ч → постмортем 5 раб.дней
- ISO 27001 / SOC 2 — roadmap Wave 4/5

## Consequences

- Защищает от 95%+ известных векторов
- Доказуемая защита для security review
- Latency +50-100ms на DLP-классификаторе

## Links

- Risks: [R-02](../risks/REGISTER.md), [R-05](../risks/REGISTER.md)
- Phases: 01.6 (sandboxing initial), 03.x (audit log), 03.x (Approval mode)
- Related ADRs: ADR-007 (auth), ADR-009 (multitenancy)
