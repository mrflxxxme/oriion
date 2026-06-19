"""tasks.outbox — grant app-role privileges + document RLS exemption (audit P3).

0005 created ``tasks.outbox`` but, unlike every other ``tasks.*`` table, never
granted ``oriion_app`` any table privileges — so the web tier's outbox WRITE
(``TaskService.add_outbox_event`` runs as ``oriion_app``) and the relay's
drain/stamp would fail with "permission denied" in production. This grants the
needed privileges.

RLS decision (audit P3): ``tasks.outbox`` is **deliberately exempt from tenant
RLS**, unlike the cell-isolated ``tasks.tasks`` / ``task_steps`` /
``task_artifacts``. The relay (``runtime.queue.outbox_relay``) drains rows
**across all tenants** with no tenant GUC set, so a ``cell_id``-isolation policy
would make the relay see zero rows and silently stop draining. The payload is
UUID-only today (task_id / cell_id / user_id — no PII or prompt text), so the
exposure of an un-isolated infra table is low and bounded. True isolation
(a dedicated BYPASSRLS relay role + RLS on the table, so a tenant session can't
read cross-tenant events while the relay still drains) is tracked as a Wave-1
follow-up; until then, keep PII/prompt text OUT of ``outbox.data``.
"""

from __future__ import annotations

from alembic import op

revision: str = "tasks_0006_outbox_grants"
down_revision: str | None = "tasks_0005_outbox"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Web tier writes (INSERT); relay drains (SELECT) + stamps published_at
    # (UPDATE). No DELETE — nothing prunes outbox rows yet (Wave-1 retention).
    op.execute("GRANT SELECT, INSERT, UPDATE ON tasks.outbox TO oriion_app;")
    op.execute(
        "COMMENT ON TABLE tasks.outbox IS "
        "'Infra/relay table — deliberately RLS-exempt: the relay drains across "
        "all tenants with no tenant GUC. Keep payload non-sensitive (UUID-only). "
        "Dedicated BYPASSRLS relay role + RLS = Wave-1 follow-up.';"
    )


def downgrade() -> None:
    op.execute("COMMENT ON TABLE tasks.outbox IS NULL;")
    op.execute("REVOKE SELECT, INSERT, UPDATE ON tasks.outbox FROM oriion_app;")
