"""Subscription + trial provisioning for the billing context.

``start_trial`` is the eager grant fired at first cell provisioning (from
``iam.auth_service.register`` via the ``TrialProvisioning`` port). It is
idempotent — re-running for a cell that already has a non-canceled subscription
is a no-op, so the register replay path never double-grants.

Grants are written to ``billing.credit_transactions`` (1 credit = 1 RUB,
Wave-0 invariant) as ``trial_grant`` / ``credit`` rows — the same ledger the
LLM gateway debits. RLS requires ``current_cell_id()`` to equal the row's
``cell_id``; callers (register, admin) set the tenant GUC first.

Rollover/expiry is deferred (Wave-1): grants are valid within
``period_start..period_end`` only; no scheduler.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.exceptions import PlanNotFound
from src.billing.models import CreditTransaction, Subscription
from src.billing.repositories import PlanRepository, SubscriptionRepository
from src.billing.services.balance_service import get_balance

logger = structlog.get_logger(__name__)

_DEFAULT_TRIAL_DAYS = 14
_DEFAULT_PERIOD_DAYS = 30


async def _record_grant(
    session: AsyncSession,
    *,
    cell_id: UUID,
    workspace_id: UUID,
    user_id: UUID | None,
    amount_credits: Decimal,
    transaction_type: str,
    reason: str,
) -> CreditTransaction:
    """Insert a balance-increasing ledger row (trial_grant / credit / refund).

    Wave-0 invariant: 1 credit = 1 RUB, so ``amount_rub == amount_credits``.
    These non-debit rows have no ``llm_usage_log`` partner — the cost
    sum-check invariant is debit-scoped.
    """
    balance_after = await get_balance(session, cell_id) + amount_credits
    row = CreditTransaction(
        cell_id=cell_id,
        workspace_id=workspace_id,
        user_id=user_id,
        task_id=None,
        transaction_type=transaction_type,
        amount_rub=amount_credits,
        amount_credits=amount_credits,
        balance_after_credits=balance_after,
        fx_rate_usd_to_rub=None,
        provider=None,
        model=None,
        tokens_input=0,
        tokens_output=0,
        payload={"reason": reason},
    )
    session.add(row)
    await session.flush()
    return row


async def start_trial(
    session: AsyncSession,
    *,
    cell_id: UUID,
    workspace_id: UUID,
    user_id: UUID,
) -> Subscription:
    """Provision the Trial subscription + included credit grant (idempotent)."""
    sub_repo = SubscriptionRepository(session)
    existing = await sub_repo.get_active_by_cell(cell_id)
    if existing is not None:
        logger.debug("billing.start_trial.idempotent_skip", cell_id=str(cell_id))
        return existing

    trial = await PlanRepository(session).get("trial")
    if trial is None:
        raise PlanNotFound("trial")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=trial.trial_days or _DEFAULT_TRIAL_DAYS)
    subscription = await sub_repo.create(
        cell_id=cell_id,
        workspace_id=workspace_id,
        plan_slug=trial.slug,
        status="trial",
        period_start=now,
        period_end=period_end,
        trial_ends_at=period_end,
        credits_granted_this_period=trial.included_credits,
    )
    await _record_grant(
        session,
        cell_id=cell_id,
        workspace_id=workspace_id,
        user_id=user_id,
        amount_credits=trial.included_credits,
        transaction_type="trial_grant",
        reason="trial_grant",
    )
    logger.info(
        "billing.start_trial.granted",
        cell_id=str(cell_id),
        credits=str(trial.included_credits),
        trial_ends_at=period_end.isoformat(),
    )
    return subscription


async def assign_plan(
    session: AsyncSession,
    *,
    cell_id: UUID,
    workspace_id: UUID,
    user_id: UUID,
    plan_slug: str,
) -> Subscription:
    """Admin/seed path: switch a cell to a paid plan + grant its credits.

    Wave-1 has no ЮKassa flow (deferred to 01.3b), so paid-plan activation is
    operator-driven. Cancels any current subscription, then activates the new
    plan with a 30-day period and a ``credit`` grant of its included credits.
    """
    plan = await PlanRepository(session).get(plan_slug)
    if plan is None:
        raise PlanNotFound(plan_slug)

    sub_repo = SubscriptionRepository(session)
    existing = await sub_repo.get_active_by_cell(cell_id)
    if existing is not None:
        await sub_repo.update_status(existing.id, "canceled")

    now = datetime.now(UTC)
    subscription = await sub_repo.create(
        cell_id=cell_id,
        workspace_id=workspace_id,
        plan_slug=plan.slug,
        status="active",
        period_start=now,
        period_end=now + timedelta(days=_DEFAULT_PERIOD_DAYS),
        trial_ends_at=None,
        credits_granted_this_period=plan.included_credits,
    )
    if plan.included_credits > Decimal(0):
        await _record_grant(
            session,
            cell_id=cell_id,
            workspace_id=workspace_id,
            user_id=user_id,
            amount_credits=plan.included_credits,
            transaction_type="credit",
            reason=f"plan:{plan.slug}",
        )
    logger.info(
        "billing.assign_plan.activated",
        cell_id=str(cell_id),
        plan_slug=plan.slug,
        credits=str(plan.included_credits),
    )
    return subscription


# ── TrialProvisioning port (Null-object pattern, mirrors agents.TeamProvisioning) ──


class TrialProvisioning(Protocol):
    """Port so ``AuthService`` depends on the trial-grant capability, not the
    concrete billing service. Unit tests inherit the no-op default; production
    wiring (``iam/deps.py``) supplies the real ``TrialProvisioningService``."""

    async def grant_trial(self, *, cell_id: UUID, workspace_id: UUID, user_id: UUID) -> None: ...


class TrialProvisioningService:
    """Real ``TrialProvisioning`` backed by ``start_trial``. The caller sets the
    3-GUC tenant context before invoking (register does)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def grant_trial(self, *, cell_id: UUID, workspace_id: UUID, user_id: UUID) -> None:
        await start_trial(
            self._session,
            cell_id=cell_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )


class NullTrialProvisioningService:
    """No-op default (unit tests / flows that don't provision billing)."""

    async def grant_trial(self, *, cell_id: UUID, workspace_id: UUID, user_id: UUID) -> None:
        logger.debug(
            "NullTrialProvisioningService — trial grant skipped (no-op default)",
            cell_id=str(cell_id),
            workspace_id=str(workspace_id),
            user_id=str(user_id),
        )


# Stateless no-op → safe as a shared module-level AuthService default.
NULL_TRIAL_PROVISIONING: TrialProvisioning = NullTrialProvisioningService()
