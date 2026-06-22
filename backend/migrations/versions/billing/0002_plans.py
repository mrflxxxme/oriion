"""billing.plans — tariff catalog (Phase 01.3, Wave 1).

Global reference/catalog table (no per-tenant RLS — same posture as the
rbac.system_roles / rbac.permissions seed tables): every tenant reads the
same tariff matrix. Authoritative tariff values per ADR-008-credits-billing.

Wave-1 scope (grill 2026-06-22): Trial + Solo are *enforced* (single-cell);
team_5/15/30 + enterprise are seeded as catalog rows only (multi-cell
provisioning + enforcement land in a follow-up once multitenancy supports
>1 cell per workspace).

per_day_cap_credits is the R-04 runaway kill-switch ceiling — seeded generous
(well above expected daily use, low enough to stop a runaway loop). Tunable.
per_task_soft/hard_credits document the ADR-008 50/100 default; Wave-1
enforcement still uses the global runtime.budget_guard constant — per-plan
task-cap override is a follow-up.

Revision ID: billing_0002_plans
Down revision: billing_0001_credit_transactions_skeleton
Branch label: billing (continued)
"""

from __future__ import annotations

from alembic import op

revision: str = "billing_0002_plans"
down_revision: str | None = "billing_0001_credit_transactions_skeleton"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE billing.plans (
            slug                    text PRIMARY KEY,
            name                    text NOT NULL,
            price_rub               numeric(12,2) NULL,
            included_credits        numeric(12,4) NOT NULL DEFAULT 0,
            cells_limit             int NULL,
            agents_limit            int NULL,
            soft_cap_credits        numeric(12,4) NULL,
            hard_cap_credits        numeric(12,4) NULL,
            per_task_soft_credits   numeric(12,4) NOT NULL DEFAULT 50,
            per_task_hard_credits   numeric(12,4) NOT NULL DEFAULT 100,
            per_day_cap_credits     numeric(12,4) NULL,
            trial_days              int NULL,
            byok_allowed            boolean NOT NULL DEFAULT false,
            byok_platform_fee_rub   numeric(12,2) NULL,
            active                  boolean NOT NULL DEFAULT true,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "COMMENT ON TABLE billing.plans IS "
        "'Tariff catalog (ADR-008). Global reference table — no RLS, read-only "
        "for oriion_app. Wave 1 enforces trial+solo; team/enterprise catalog-only.';"
    )

    op.execute(
        """
        CREATE TRIGGER plans_set_updated_at
            BEFORE UPDATE ON billing.plans
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # ── seed: 6 tiers per ADR-008 ──────────────────────────────────────────
    # Columns: slug, name, price_rub, included_credits, cells_limit,
    # agents_limit, soft_cap, hard_cap, per_task_soft, per_task_hard,
    # per_day_cap, trial_days, byok_allowed, byok_platform_fee_rub, active
    op.execute(
        """
        INSERT INTO billing.plans (
            slug, name, price_rub, included_credits, cells_limit, agents_limit,
            soft_cap_credits, hard_cap_credits, per_task_soft_credits,
            per_task_hard_credits, per_day_cap_credits, trial_days,
            byok_allowed, byok_platform_fee_rub, active
        ) VALUES
            ('trial',      'Trial',      0,    500,  1,    3,    400,  500,   50, 100, 150, 14,   false, NULL, true),
            ('solo',       'Solo',       990,  300,  1,    3,    450,  600,   50, 100, 150, NULL, true,  490,  true),
            ('team_5',     'Команда 5',  1900, 600,  3,    5,    900,  1200,  50, 100, 200, NULL, true,  890,  true),
            ('team_15',    'Команда 15', 4900, 2000, 5,    15,   3000, 4000,  50, 100, 400, NULL, true,  2400, true),
            ('team_30',    'Команда 30', 9900, 5000, 10,   30,   7500, 10000, 50, 100, 800, NULL, true,  4900, true),
            ('enterprise', 'Enterprise', NULL, 0,    NULL, NULL, NULL, NULL,  50, 100, NULL, NULL, true,  NULL, false)
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    op.execute("GRANT SELECT ON billing.plans TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS plans_set_updated_at ON billing.plans;")
    op.execute("DROP TABLE IF EXISTS billing.plans;")
