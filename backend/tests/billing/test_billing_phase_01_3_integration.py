"""Phase 01.3 billing — real-PG integration tests.

RLS only enforces when the connection is NOT a superuser, so every test runs
``SET LOCAL ROLE oriion_app`` (the testcontainer connects as the superuser
``oriion``) — mirrors tests/multitenancy/test_bootstrap_first_workspace_function.

billing.{subscriptions, credit_transactions}.cell_id are bare UUID columns (no
FK to multitenancy.cells), so synthetic cell ids are sufficient for isolation
tests. Cap tests use a back-dated subscription + back-dated debits to decouple
the per-day window from the per-period window (on a fresh trial they coincide).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.billing.exceptions import CellQuotaExceeded, DailyQuotaExceeded, PlanNotFound
from src.billing.models import CreditTransaction
from src.billing.repositories import PlanRepository, SubscriptionRepository
from src.billing.services import balance_service
from src.billing.services.quota_service import enforce_quota_admission
from src.billing.services.subscription_service import assign_plan, start_trial

pytestmark = pytest.mark.integration


async def _enter_cell(session: AsyncSession, *, ws: UUID, cell: UUID, user: UUID) -> None:
    """Activate RLS as oriion_app + bind the 3 tenant GUCs to ``cell``."""
    await session.execute(text("SET LOCAL ROLE oriion_app"))
    await session.execute(
        text("SELECT set_config('app.current_user_id', :v, true)"), {"v": str(user)}
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :v, true)"), {"v": str(ws)}
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :v, true)"), {"v": str(cell)}
    )


async def _debit(
    session: AsyncSession,
    *,
    ws: UUID,
    cell: UUID,
    user: UUID,
    credits: Decimal,
    when: datetime,
) -> None:
    session.add(
        CreditTransaction(
            cell_id=cell,
            workspace_id=ws,
            user_id=user,
            task_id=None,
            transaction_type="debit",
            amount_rub=credits,
            amount_credits=credits,
            balance_after_credits=Decimal(0),
            fx_rate_usd_to_rub=Decimal("100"),
            provider="deepseek",
            model="deepseek-chat",
            tokens_input=10,
            tokens_output=10,
            created_at=when,
        )
    )
    await session.flush()


async def test_plans_seeded(db_session: AsyncSession) -> None:
    """AC-01.3.1: the 6 ADR-008 tiers are seeded with the expected values."""
    await db_session.execute(text("SET LOCAL ROLE oriion_app"))
    plans = {p.slug: p for p in await PlanRepository(db_session).list_all()}
    assert set(plans) == {"trial", "solo", "team_5", "team_15", "team_30", "enterprise"}
    assert plans["trial"].included_credits == Decimal("500")
    assert plans["trial"].trial_days == 14
    assert plans["trial"].hard_cap_credits == Decimal("500")
    assert plans["trial"].byok_allowed is False
    assert plans["solo"].price_rub == Decimal("990")
    assert plans["solo"].byok_allowed is True


async def test_rls_isolation_subscription_and_ledger(db_session: AsyncSession) -> None:
    """AC-01.3.2: cell B cannot see cell A's subscription or ledger rows."""
    ws, user = uuid4(), uuid4()
    cell_a, cell_b = uuid4(), uuid4()

    await _enter_cell(db_session, ws=ws, cell=cell_a, user=user)
    await start_trial(db_session, cell_id=cell_a, workspace_id=ws, user_id=user)
    assert await balance_service.get_balance(db_session, cell_a) == Decimal("500")

    # Switch to cell B: A's rows are invisible under RLS.
    await _enter_cell(db_session, ws=ws, cell=cell_b, user=user)
    assert await SubscriptionRepository(db_session).get_active_by_cell(cell_a) is None
    assert await balance_service.get_balance(db_session, cell_a) == Decimal("0")
    assert await balance_service.get_balance(db_session, cell_b) == Decimal("0")


async def test_start_trial_idempotent(db_session: AsyncSession) -> None:
    """AC-01.3.3: re-running start_trial is a no-op — one sub, one 500 grant."""
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)

    sub1 = await start_trial(db_session, cell_id=cell, workspace_id=ws, user_id=user)
    sub2 = await start_trial(db_session, cell_id=cell, workspace_id=ws, user_id=user)
    assert sub1.id == sub2.id
    assert sub1.status == "trial"
    assert sub1.trial_ends_at is not None

    grants = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM billing.credit_transactions "
                "WHERE cell_id = :c AND transaction_type = 'trial_grant'"
            ),
            {"c": str(cell)},
        )
    ).scalar_one()
    assert grants == 1
    assert await balance_service.get_balance(db_session, cell) == Decimal("500")


async def test_balance_period_and_daily_usage(db_session: AsyncSession) -> None:
    """AC-01.3.4 + AC-01.3.9: balance/usage = ledger SUM; debits reconcile."""
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)
    sub = await start_trial(db_session, cell_id=cell, workspace_id=ws, user_id=user)

    await _debit(
        db_session, ws=ws, cell=cell, user=user, credits=Decimal("30"), when=datetime.now(UTC)
    )

    assert await balance_service.get_balance(db_session, cell) == Decimal("470")
    assert await balance_service.get_period_usage(
        db_session, cell, period_start=sub.period_start
    ) == Decimal("30")
    assert await balance_service.get_daily_usage(db_session, cell) == Decimal("30")

    # AC-01.3.9: SUM of debit rows equals total usage.
    debit_sum = (
        await db_session.execute(
            text(
                "SELECT coalesce(sum(amount_rub),0) FROM billing.credit_transactions "
                "WHERE cell_id = :c AND transaction_type = 'debit'"
            ),
            {"c": str(cell)},
        )
    ).scalar_one()
    assert Decimal(debit_sum) == Decimal("30")


async def test_per_cell_hard_block_and_soft_warn(db_session: AsyncSession) -> None:
    """AC-01.3.5: per-cell period hard-cap blocks; soft-cap warns (no block).

    Uses a back-dated solo subscription (period started 10d ago) + a debit dated
    5d ago so the per-day window (today) stays empty and only the period cap is
    in play. Solo: soft 450 / hard 600 / per-day 150.
    """
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)
    now = datetime.now(UTC)
    await SubscriptionRepository(db_session).create(
        cell_id=cell,
        workspace_id=ws,
        plan_slug="solo",
        status="active",
        period_start=now - timedelta(days=10),
        period_end=now + timedelta(days=20),
        trial_ends_at=None,
        credits_granted_this_period=Decimal("300"),
    )

    # Soft-cap: 470 used (>=450 soft, <600 hard), none today → warn, no raise.
    await _debit(
        db_session,
        ws=ws,
        cell=cell,
        user=user,
        credits=Decimal("470"),
        when=now - timedelta(days=5),
    )
    status = await enforce_quota_admission(db_session, cell)
    assert status.enforced is True
    assert status.soft_warn is True

    # Push over the hard cap (total 620 >= 600) → CellQuotaExceeded.
    await _debit(
        db_session,
        ws=ws,
        cell=cell,
        user=user,
        credits=Decimal("150"),
        when=now - timedelta(days=5),
    )
    with pytest.raises(CellQuotaExceeded):
        await enforce_quota_admission(db_session, cell)


async def test_per_day_kill_switch(db_session: AsyncSession) -> None:
    """AC-01.3.6: today's usage >= per-day cap → DailyQuotaExceeded (R-04)."""
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)
    await start_trial(db_session, cell_id=cell, workspace_id=ws, user_id=user)

    # Trial per-day cap is 150; spend it all today.
    await _debit(
        db_session, ws=ws, cell=cell, user=user, credits=Decimal("150"), when=datetime.now(UTC)
    )
    with pytest.raises(DailyQuotaExceeded):
        await enforce_quota_admission(db_session, cell)


async def test_assign_plan_activates_and_grants(db_session: AsyncSession) -> None:
    """assign_plan cancels the trial, activates the paid plan + grants credits."""
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)
    await start_trial(db_session, cell_id=cell, workspace_id=ws, user_id=user)

    sub = await assign_plan(
        db_session, cell_id=cell, workspace_id=ws, user_id=user, plan_slug="solo"
    )
    assert sub.status == "active"
    assert sub.plan_slug == "solo"

    active = await SubscriptionRepository(db_session).get_active_by_cell(cell)
    assert active is not None
    assert active.id == sub.id  # the trial is canceled; solo is now active

    # 500 (trial grant) + 300 (solo included) = 800
    assert await balance_service.get_balance(db_session, cell) == Decimal("800")


async def test_assign_plan_unknown_slug_raises(db_session: AsyncSession) -> None:
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)
    with pytest.raises(PlanNotFound):
        await assign_plan(db_session, cell_id=cell, workspace_id=ws, user_id=user, plan_slug="nope")


async def test_no_subscription_is_noop(db_session: AsyncSession) -> None:
    """Admission is a no-op for a cell with no active subscription (back-compat
    for cells created outside the register flow)."""
    ws, user, cell = uuid4(), uuid4(), uuid4()
    await _enter_cell(db_session, ws=ws, cell=cell, user=user)
    status = await enforce_quota_admission(db_session, cell)
    assert status.enforced is False
    assert status.soft_warn is False
