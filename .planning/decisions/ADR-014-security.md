# ADR-014: Security — RBAC + DLP + изоляция memory от tool-output + операционная гигиена

- **Status:** Accepted

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
