"""AC-W1-2 + AC-W1-13: per-delegation task_steps + real-ledger billing on real PG.

``record_delegation_step`` is the production step recorder the leaf runner calls
once per delegation. On a real Postgres it must:

* **AC-W1-13** — bill the call through the REAL ledger: write ``llm_usage_log`` +
  ``credit_transactions`` rows priced by the V4 ``pricing_service`` (replacing the
  Wave-0 ``estimate_credits``); the returned credit cost == ``cost_rub``.
* **AC-W1-2** — persist a ``task_steps`` row on the parent with the token split +
  a non-zero ``cost_credits``, so ``task.total_cost_credits == SUM(steps)`` (the
  ``cost_rollup_service`` invariant).

Owner-role INSERTs seed workspace + cell + archetypes + the parent task (the DB
owner bypasses FORCE-RLS, same pattern as ``test_cancel_cascade_integration``).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

# Register cross-context models so the string-based FKs resolve at flush time.
import src.agents.models
import src.billing.models
import src.llm_gateway.models
import src.multitenancy.models  # noqa: F401
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.llm_gateway.services.pricing_service import calculate_cost_usd_and_rub, get_fx_rate
from src.runtime.dispatch import StepBilling, record_delegation_step
from src.tasks.services.cost_rollup_service import rollup_task_cost

pytestmark = [pytest.mark.integration, pytest.mark.commit_required]

# (slug, role_category) — role_category is CHECK-constrained; 'analyst' maps to
# the 'analyzer' category. The leaf slugs the Coordinator delegates to.
_LEAVES = [("researcher", "researcher"), ("analyst", "analyzer"), ("writer", "writer")]
_TOKENS_IN = 1000
_TOKENS_OUT = 2000
_PROVIDER = "deepseek"
_MODEL = "deepseek-chat"


async def _seed(session: AsyncSession) -> tuple[UUID, UUID, UUID]:
    """Insert workspace + cell + 3 archetypes + a running parent task (owner role).

    Returns ``(cell_id, parent_task_id, user_id)``.
    """
    workspace_id, cell_id, user_id, parent_id = uuid4(), uuid4(), uuid4(), uuid4()
    suffix = str(workspace_id)[:8]
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(workspace_id), "slug": f"steps-{suffix}", "name": "Steps Billing WS"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'Default')"
        ),
        {"id": str(cell_id), "ws": str(workspace_id)},
    )
    for slug, role_category in _LEAVES:
        await session.execute(
            text(
                "INSERT INTO agents.agent_archetypes "
                "(id, slug, vertical_slug, display_name, role_category, prompt_version, "
                " model_provider_slug, model_name) "
                "VALUES (:id, :slug, 'productivity-core', :dn, :rc, 'v1', 'deepseek', "
                " 'deepseek-chat')"
            ),
            {"id": str(uuid4()), "slug": slug, "dn": slug.title(), "rc": role_category},
        )
    await session.execute(
        text(
            "INSERT INTO tasks.tasks (id, cell_id, initiated_by_user_id, title, description, status) "
            "VALUES (:id, :cell, :user, 'parent', '', 'running')"
        ),
        {"id": str(parent_id), "cell": str(cell_id), "user": str(user_id)},
    )
    # 3-GUC tenant context so any RLS policy on task_steps accepts the INSERTs.
    for guc, val in (
        ("app.current_user_id", user_id),
        ("app.current_cell_id", cell_id),
        ("app.current_workspace_id", workspace_id),
    ):
        await session.execute(text("SELECT set_config(:k, :v, true)"), {"k": guc, "v": str(val)})
    return cell_id, parent_id, user_id


async def test_each_delegation_writes_step_and_real_cost(
    db_session_committed: AsyncSession,
) -> None:
    session = db_session_committed
    cell_id, parent_id, user_id = await _seed(session)

    # Sanity: the V4 pricing table yields a real, non-zero cost (not the estimate).
    expected_rub = calculate_cost_usd_and_rub(
        _PROVIDER, _MODEL, _TOKENS_IN, _TOKENS_OUT, get_fx_rate()
    )[1]
    assert expected_rub > 0

    for i, (slug, _rc) in enumerate(_LEAVES, start=1):
        cost = await record_delegation_step(
            session,
            StepBilling(
                parent_task_id=parent_id,
                cell_id=cell_id,
                user_id=user_id,
                step_index=i,
                target_agent_slug=slug,
                provider_slug=_PROVIDER,
                model_name=_MODEL,
                input_tokens=_TOKENS_IN,
                output_tokens=_TOKENS_OUT,
                latency_ms=42,
            ),
        )
        assert cost == expected_rub  # AC-W1-13: real cost_rub, not estimate

    # AC-W1-2: one task_steps row per delegation, each with non-zero cost.
    step_rows = (
        await session.execute(
            text(
                "SELECT step_index, step_type, cost_credits FROM tasks.task_steps "
                "WHERE task_id = :t ORDER BY step_index"
            ),
            {"t": str(parent_id)},
        )
    ).all()
    assert [r[0] for r in step_rows] == [1, 2, 3]
    assert all(r[1] == "delegation" for r in step_rows)
    assert all(r[2] > 0 for r in step_rows)

    # AC-W1-13: the real ledger was written (one usage row + one debit per call).
    usage_count = (
        await session.execute(
            text("SELECT count(*) FROM llm_gateway.llm_usage_log WHERE task_id = :t"),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    debit_count = (
        await session.execute(
            text(
                "SELECT count(*) FROM billing.credit_transactions "
                "WHERE task_id = :t AND transaction_type = 'debit'"
            ),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    assert usage_count == 3
    assert debit_count == 3

    # AC-W1-2: task.total_cost_credits == SUM(task_steps.cost_credits).
    rolled = await rollup_task_cost(parent_id, session)
    steps_sum = (
        await session.execute(
            text("SELECT coalesce(sum(cost_credits), 0) FROM tasks.task_steps WHERE task_id = :t"),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    persisted = (
        await session.execute(
            text("SELECT total_cost_credits FROM tasks.tasks WHERE id = :t"),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    assert rolled == steps_sum == persisted == expected_rub * 3
