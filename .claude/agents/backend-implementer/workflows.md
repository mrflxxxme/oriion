# backend-implementer — workflows

Четыре canonical playbook'а.

---

## Workflow 1 — Implement new endpoint from api.yaml

**Trigger:** `tech.oriion.plan.task.v1` с task type «implement endpoint» (e.g. T3: «POST
/auth/login per _meta/contracts/iam/api.yaml»).

**Inputs:**
- Task description + `contract_refs` (e.g. `_meta/contracts/iam/api.yaml#/paths/~1auth~1login`)
- PLAN.md (full context)
- `_meta/contracts/iam/api.yaml`, `schema.sql`, `events.yaml`, `README.md`
- Existing `backend/src/iam/` structure

**Steps:**

1. **Read contract** `_meta/contracts/iam/api.yaml` — extract:
   - Path, method, request body schema, response body schema, status codes
   - Auth requirements (security schemes)
   - Tags (для router grouping)

2. **Verify dependencies.** If endpoint requires User model (per request/response schema):
   - Check `src/iam/models.py` has `User` SQLAlchemy model
   - If not — это predecessor task, проверь dependency ordering в PLAN.md
   - Если depends_on не выполнен — abort task, log dependency violation

3. **Check existing impl.** Grep router files — endpoint уже implemented?
   - If yes (re-plan cycle): read existing implementation, identify diff per revision doc
   - If no: greenfield implementation

4. **Implement Pydantic schemas.** В `src/iam/schemas.py`:
   ```python
   class LoginRequest(BaseModel):
       model_config = ConfigDict(from_attributes=True, populate_by_name=True)
       email: EmailStr = Field(...)
       password: str = Field(..., min_length=8)

   class LoginResponse(BaseModel):
       access_token: str
       refresh_token: str
       token_type: Literal["bearer"] = "bearer"
       expires_in: int
   ```
   Fields ↔ api.yaml schemas 1:1.

5. **Implement service** в `src/iam/services/auth_service.py`:
   - Async function `login(email, password) -> tuple[User, AccessToken, RefreshToken]`
   - Inject `UserRepository`, `TokenService`
   - Business logic: verify password, issue tokens, log audit event
   - Emit CloudEvent (`tech.oriion.iam.login.v1`) per `events.yaml`

6. **Implement router** в `src/iam/routers/auth.py`:
   ```python
   router = APIRouter(prefix="/auth", tags=["iam"])

   @router.post("/login", response_model=LoginResponse, status_code=200)
   async def login(
       payload: LoginRequest,
       auth_service: AuthService = Depends(get_auth_service),
   ) -> LoginResponse:
       user, access, refresh = await auth_service.login(payload.email, payload.password)
       return LoginResponse(
           access_token=access.token,
           refresh_token=refresh.token,
           expires_in=access.expires_in,
       )
   ```

7. **Add tests** в `backend/tests/iam/`:
   - `test_schemas.py::test_login_request_validation` (unit)
   - `test_auth_service.py::test_login_success` (unit с mocked repo)
   - `test_auth_endpoint.py::test_post_login_returns_tokens` (integration с test DB)
   - Acceptance check из PLAN.md mapped to specific test name

8. **Run tests locally** через Bash: `pytest backend/tests/iam/test_auth_endpoint.py -v`.
   Если fail — fix iteratively до pass.

9. **Run lint** через Bash: `ruff check backend/src/iam/ && mypy --strict backend/src/iam/`.
   Fix до clean.

10. **Self-audit per checklist** (`checklists/endpoint-checklist.md`).

11. **Atomic commit** per ADR-027 §4:
    ```
    feat(iam): add POST /auth/login endpoint

    Phase: 00.2
    Pipeline-role: backend-implementer
    Reviewers: pending
    ADR-refs: ADR-007, ADR-014

    Co-Authored-By: backend-implementer (Opus) <backend-implementer@teamly-ai>
    ```

12. **Update PLAN.md status column** для этой task: `IN-PROGRESS` → `DONE`.

**Outputs:**
- Code commits (typically 1-3 per endpoint: schemas, service, router+tests)
- Updated PLAN.md status

**Handoff:** `tech.oriion.code.commit.v1` к `reviewer-backend` ∥ `reviewer-security`.

---

## Workflow 2 — Add migration from schema.sql diff

**Trigger:** `tech.oriion.plan.task.v1` с task type «add migration» (e.g. T1: «Alembic
migration: add users table per _meta/contracts/iam/schema.sql»).

**Inputs:**
- Task description с `contract_refs` (path к schema.sql + table name)
- `_meta/contracts/iam/schema.sql` (authoritative DDL)
- Existing `backend/alembic/versions/iam/*.py`
- `alembic.ini` для multi-version directory config

**Steps:**

1. **Read authoritative DDL** из `_meta/contracts/iam/schema.sql`. Extract:
   - CREATE TABLE statements для target table
   - Indices (CREATE INDEX)
   - Constraints (UNIQUE, FK, CHECK)
   - RLS policies (ENABLE ROW LEVEL SECURITY + CREATE POLICY)
   - Defaults

2. **Check existing migrations** в `backend/alembic/versions/iam/`. Identify:
   - Latest revision (для `down_revision` field)
   - Highest sequence number (для filename `NNNN_<slug>.py`)

3. **Generate migration file** `backend/alembic/versions/iam/0001_users.py`:
   ```python
   """add users table

   Revision ID: <generated>
   Revises: <previous>
   Create Date: 2026-06-15 14:30:00
   """
   from alembic import op
   import sqlalchemy as sa
   from sqlalchemy.sql import text

   revision = "<sha>"
   down_revision = "<previous-or-none>"

   def upgrade() -> None:
       op.create_table(
           "users",
           sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
           sa.Column("email", sa.String(255), nullable=False),
           sa.Column("password_hash", sa.String(255), nullable=False),
           sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
           # ...
       )
       op.create_index("ix_users_email", "users", ["email"], unique=True)
       # RLS
       op.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
       op.execute(text("""
           CREATE POLICY users_tenant_isolation ON users
           USING (organization_id = current_setting('app.current_tenant')::uuid)
       """))

   def downgrade() -> None:
       op.execute(text("DROP POLICY IF EXISTS users_tenant_isolation ON users"))
       op.drop_index("ix_users_email", "users")
       op.drop_table("users")
   ```

4. **Verify diff to schema.sql 1:1.** Every column, index, RLS policy в migration matches
   schema.sql. Any divergence — STOP, escalate к architect.

5. **Test migration locally:**
   ```bash
   alembic -c backend/alembic.ini upgrade head
   alembic -c backend/alembic.ini downgrade -1
   alembic -c backend/alembic.ini upgrade head
   ```
   All steps должны succeed. Test rollback critical per checklist.

6. **Add migration test** в `backend/tests/iam/test_migrations.py`:
   - Test table exists after upgrade
   - Test RLS policy active (verify через `pg_policies` query)
   - Test downgrade cleans up

7. **Self-audit per checklist** (`checklists/migration-checklist.md`).

8. **Atomic commit:**
   ```
   feat(iam): add users table migration

   Phase: 00.2
   Pipeline-role: backend-implementer
   Reviewers: pending
   ADR-refs: ADR-007, ADR-009

   Co-Authored-By: backend-implementer (Opus) <backend-implementer@teamly-ai>
   ```

9. **Update PLAN.md status.**

**Outputs:**
- Migration file
- Migration test
- Updated PLAN.md

**Handoff:** `tech.oriion.code.commit.v1` к reviewers.

---

## Workflow 3 — Emit CloudEvent from events.yaml

**Trigger:** task type «emit CloudEvent» (e.g. T5: «Emit tech.oriion.iam.login.v1 per
_meta/contracts/iam/events.yaml»).

**Inputs:**
- Task + `contract_refs` (events.yaml path + event type)
- `_meta/contracts/iam/events.yaml` (authoritative event spec)
- Existing `src/iam/events.py` (если есть)
- Project `EventBus` interface (typically `src/_shared/events.py`)

**Steps:**

1. **Read event spec** `_meta/contracts/iam/events.yaml`:
   - `type` field exact value
   - `data` schema (Pydantic-able)
   - `subject` format
   - Consumers list (для documentation)

2. **Implement Pydantic event payload** в `src/iam/events.py`:
   ```python
   class LoginEventData(BaseModel):
       user_id: UUID
       login_at: datetime
       ip_address: str
       user_agent: str | None = None
   ```

3. **Implement emit helper:**
   ```python
   from cloudevents.http import CloudEvent
   from src._shared.events import event_bus

   async def emit_login_event(data: LoginEventData) -> None:
       event = CloudEvent(
           attributes={
               "type": "tech.oriion.iam.login.v1",
               "source": "claude-agent://backend-implementer/iam",
               "subject": str(data.user_id),
               "datacontenttype": "application/json",
           },
           data=data.model_dump(mode="json"),
       )
       await event_bus.publish(event)
   ```

4. **Wire into service.** В `auth_service.login()`:
   ```python
   await emit_login_event(LoginEventData(
       user_id=user.id,
       login_at=datetime.now(UTC),
       ip_address=request.client.host,
   ))
   ```

5. **Add test:**
   - Unit test event payload schema
   - Integration test verifying event bus receives event на login

6. **Atomic commit** + update PLAN.md status.

**Handoff:** `tech.oriion.code.commit.v1` к reviewers.

---

## Workflow 4 — Fix from reviewer revision-request

**Trigger:** `tech.oriion.plan.task.v1` (re-dispatched от `planner` после re-plan) с
tasks для changed scope. Revision context: `revisions/<phase>-reviewer-*.md`.

**Inputs:**
- Updated PLAN.md (Cycle: 2 of 3 или 3 of 3)
- `revisions/<phase>-reviewer-<role>.md` — findings table
- Existing commits на feature-branch (через git log)

**Steps:**

1. **Read revision doc fully.** Each finding: file:line, expected, actual, severity.
   Don't paraphrase — match exact location.

2. **Group findings.**
   - **Blocker / High** — fix per finding
   - **Medium / Low** — defer ОК per founder policy, но если cycle < 3 — лучше пофиксить
   - Если finding requires contract change — escalate к architect, не silent fix

3. **For each finding:**
   - Read the cited file:line
   - Apply fix per «expected» description
   - Add test reproducing the issue (regression-prevention)
   - Run tests + lint

4. **NO `git commit --amend`.** Per ADR-027 §6: новый commit для каждого fix.
   Commit message:
   ```
   fix(iam): rate-limit /auth/refresh per reviewer-security

   Phase: 00.2
   Pipeline-role: backend-implementer
   Reviewers: pending (re-review)
   ADR-refs: ADR-014
   Addresses: revisions/00.2-reviewer-security.md#finding-3

   Co-Authored-By: backend-implementer (Opus) <backend-implementer@teamly-ai>
   ```

5. **Update PLAN.md status** for affected tasks: revert `DONE` → `IN-PROGRESS` →
   `DONE` после fix.

6. **Per finding checklist** — addressed findings count = total blocker + high.

**Handoff:** `tech.oriion.code.commit.v1` к reviewers (re-review).
