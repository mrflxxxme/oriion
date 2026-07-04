# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-04 (**Phase 01.7 RBAC (Owner + Member) — `/autonomy:run`, code-complete**)
- Session: autonomous runner (ADR-037), branch `claude/auto-01.7-rbac`
- Agent: @claude

## Project status

- **Wave:** Wave 1 (Core MVP) — in progress. 01.1-retro ✅ · 01.2 ✅ · 01.3 ✅ · 01.4 ✅ · 01.4b ✅ · 01.5 ✅ · 01.6 ✅ (merged `#84`) · **01.7 = this PR**.
- **01.7 «RBAC (Owner + Member)» ([ADR-014](./decisions/ADR-014-security.md) §1):** enforcement поверх уже-собранного RBAC data-layer. **Option A (flat visibility)** — грил 2026-07-03 founder-approved: все члены cell видят все артефакты (RLS уже по `cell_id`; Member = cell-доступ); Owner vs Member различаются ТОЛЬКО в правах. Admin/Viewer → Wave 2.
- **Gap → что добавила фаза:** каталог permissions/ролей/грантов + `has_permission` уже были; дыра = **enforcement** (0 permission-check'ов в роутерах) + `rbac.role_assignments` (который читает `has_permission`) никем не пишется. Enforcement построен на **`multitenancy.cell_members.role_id`** (populated store: Owner ставится на register, редактируется через cells-роутер) через новый `AuthorizationService.has_cell_permission` (джойн `cell_members → role_permissions → permissions`). Гвард `require_cell_permission(slug)` в `src/rbac/deps.py` → 403 `PermissionDenied` (RbacError-handler в `main.py`).
- **Owner-only enforcement применён:** `cells.py` — invite / role-change / remove-member + **новый** `DELETE /cells/{cell_id}` (archive); `billing.py` — `billing.view` на cell-scoped `subscription`/`balance`/`transactions` (global `credit-rate`/`plans` открыты). Member: task-create + все reads (`get_cell`/`list_members` не gated — flat visibility).
- **`artifacts.visibility` stub:** миграция `artifacts/0002_artifact_visibility_stub.py` — `visibility text NOT NULL DEFAULT 'cell-shared'` + CHECK `('cell-shared','private')`, default-backfill (без отдельного pass), **НЕ enforced** нигде (задел под Option B per-artifact privacy в Wave-2). Контракт `contracts/artifacts/schema.sql` + ORM `artifacts/models.py` обновлены 1:1.
- **Adversarial audit (3 линзы, refute-by-default):** SECURE ✅ PASS (0 P0/P1 — cross-tenant/priv-esc/injection опровергнуты: RLS-scoped + explicit cell/user фильтр + параметризованный SELECT + default-deny) · SOUND ✅ PASS (гвард = hard dependency, raise до тела, нет bypass) · NO-REGRESSIONS ✅ PASS (956 unit green; billing-E2E + cells_router обновлены под гвард и зелёные).
- **Gates финального кода:** ruff clean (423 files) · mypy --strict 226 (0 issues) · bandit 0 · unit 956 passed / 2 skipped (env-gated) · integration 29 passed (real PG, Docker up) · `src/rbac` coverage **100%**. Live/LLM не требуются.

## Pending founder actions

**Блокирующий: `/autonomy:ack`** — фаза задевает tripwire. PR трогает `src/rbac` + auth-adjacent surface **и** содержит миграцию (`artifacts/0002`), которая **ALTER'ит** existing table → tripwire = `auth_rbac_sessions` + `db_migrations`. Миграция НЕ pure-CREATE (ADD COLUMN на существующей таблице) → **не авто-мёрж, нужен founder ack**. Это ожидаемо и корректно (грил 2026-07-03 заранее это отметил).

Deferred (НЕ блокирует merge):
1. **P3** — `has_permission` (role_assignments) теперь dead-store в Wave-1; сохранён намеренно как шов под Wave-2 workspace-scoped/delegated гранты. Если Wave-2 не задействует — вернуться к удалению.
2. **P3** — гвард резолвит cell через tenant-context single-cell (Wave-0 инвариант 1 user → 1 cell), а cells-роутер берёт `cell_id` из path; совпадают в Wave-0. При multi-cell membership + `active_cell` JWT-claim (Wave-1+) согласовать `get_current_cell_id` с path-параметром.
3. **P3** — billing writes пока нет; при появлении gate'ить `billing.manage` (Owner/billing-роль) тем же фактори.

## Active blockers (none block this PR beyond the ack)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## Next product phase

Wave-1 продолжается. RBAC enforcement (01.7) разблокирует любые Owner-gated surface последующих фаз. Admin/Viewer роли + Option B (per-artifact privacy, флип `visibility` stub → enforced через RLS/service-change, без миграции) — Wave 2.
