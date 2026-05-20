# ADR-014: Security — RBAC + DLP + изоляция memory от tool-output + операционная гигиена

- **Status:** Accepted (amendments 2026-05-19 + 2026-05-20, see «Wave 0 security decisions»)

## Pip-audit ignored advisories registry (audit-trail)

> Each ignored advisory MUST be re-reviewed at the next dependency bump
> of the affected package. CI hooks: `.github/workflows/ci-backend.yml`
> step `pip-audit (CVE scan)`.

| Advisory | Package | Status | Justification | Re-review trigger |
|---|---|---|---|---|
| `PYSEC-2025-183` / `CVE-2025-45768` | `pyjwt` (all versions) | DISPUTED by upstream (jpadilla) | Claim is "weak encryption when key length is short". Our policy: HS256 + mandatory 32+ char secret per `Settings.jwt_secret_access_v1` field default literally encoding "min-32-chars". No fix version published; advisory has no upper-bound (all versions marked affected). | Re-review at every `pyjwt` bump or when fix version published |
| `CVE-2025-69872` | `diskcache` 5.6.3 (transitive via `fastmcp` → `pydantic-ai`) | No fix version published as of 2026-05-21 | Not on a runtime critical path for our stack — used internally by `fastmcp` for its own request-caching layer, not for user data or BYOK key material. The other 5 transitive CVEs (CVE-2026-25580 / GHSA-rcfx-77hg-w2wv / CVE-2025-69196 / CVE-2025-64340 / CVE-2026-27124) were closed by bumping pydantic-ai → 1.56+ and fastmcp → 3.2+ in Phase 00.5b post-PR-CI fix. | Re-review when `diskcache` publishes a fix or when `fastmcp` drops the dep |

## Wave 0 security decisions (2026-05-19, amended 2026-05-20)

> Adopted in the pre-Phase-00.3 contract extension (Phase 00.3 + 00.4 combined PR).
> Honesty-pass amendment 2026-05-20: Phase 00.5 Topic 1 RLS Option A landed
> the practical bootstrap escape (per F-ST-4 deferral from pre-Phase-05 audit).
> The amendment below replaces the original «3-GUC default-deny RLS posture»
> bullet with a truthful statement of the register-time exception.

1. **3-GUC default-deny RLS posture with documented bootstrap exception** (amended 2026-05-20):
    - **Production behaviour.** App connections use the non-superuser `oriion_app`
      role (no BYPASSRLS). Every request handler depends on
      `_shared.middleware.tenant_context.get_tenant_db_session` which sets
      `app.current_user_id` + `app.current_workspace_id` + `app.current_cell_id`
      session locals per transaction via `_shared.db.rls.set_tenant_context`.
      Missing GUC → `_shared.current_*_id()` helpers return `NULL` →
      multitenancy + per-cell RLS policies evaluate FALSE → zero rows visible.
    - **Register-time bootstrap exception.** `POST /auth/register` cannot satisfy
      the FORCE-RLS INSERT WITH CHECK policies on
      `multitenancy.{workspaces, cells, cell_members}` — the just-created user
      has no session yet, hence no tenant GUC. Per Phase 00.5 Topic 1
      (founder-resolved 2026-05-20, RLS Option A), the bootstrap is delegated
      to the SECURITY DEFINER SQL function
      `multitenancy.bootstrap_first_workspace(p_user_id, p_workspace_slug,
      p_display_name)` introduced in migration
      `multitenancy/0005_bootstrap_first_workspace_function.py`. The function
      runs with migration-owner privileges (BYPASSRLS) for the four bootstrap
      INSERTs + per-cell schema provisioning, returns `(workspace_id, cell_id,
      schema_name, was_replay)`. This is the SOLE production-callable owner-
      context path; every other endpoint uses `oriion_app` with GUC.
    - **Companion helper for the middleware itself.**
      `multitenancy.resolve_user_first_membership(p_user_id) RETURNS TABLE(
      workspace_id uuid, cell_id uuid)` is the second SECURITY DEFINER helper
      (same migration). The tenant_context middleware uses it to look up the
      user's first membership BEFORE the GUC is set (chicken-and-egg). Wave-0
      single-membership simplification; Wave-1+ replaces with an
      `active_workspace_id` JWT claim.
    - **CI assertion of production failure mode.**
      `backend/tests/integration/test_e2e_auth_flow.py::override_get_db`
      issues `SET LOCAL ROLE oriion_app` so the integration suite surfaces
      the RLS posture that prod will actually see (instead of silently
      bypassing FORCE RLS as the testcontainers DB owner).
    - **Direct DB-owner credentials never used by app code.** The two
      SECURITY DEFINER functions above are the entire surface; any future
      bootstrap-class operation needs the same pattern + an ADR amendment.
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
