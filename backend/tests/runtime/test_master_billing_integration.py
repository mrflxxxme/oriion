"""AC-W1-3.3/3.4 on real PG: Master LLM-call billing + step-sum cost authority.

``record_master_call_step`` is the production recorder for a Master's own
plan/synthesis LLM calls. On a real Postgres it must:

* Resolve the FK to the **Master archetype of the right vertical** (AC-W1-3.3 —
  the multi-vertical disambiguation the leaf path's slug-only lookup can't do).
* Write a ``task_steps`` row with ``step_type='llm_call'`` + real ledger cost.

Combined with the leaf ``record_delegation_step`` rows, the per-task step-sum
(``task.total_cost_credits`` authority) equals plan + synthesis + delegations
with NO double-count from the lineage child tasks (AC-W1-3.4).

Owner-role INSERTs seed workspace + cell + archetypes + the parent task, same
pattern as ``tests/tasks/test_task_steps_billing_integration.py``.
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
from src.agents.master import MasterCallBilling
from src.runtime.dispatch import StepBilling, record_delegation_step, record_master_call_step

pytestmark = [pytest.mark.integration, pytest.mark.commit_required]

_VERTICAL = "agency_marketing_ru"
_PROVIDER = "deepseek"
_MODEL = "deepseek-chat"
_LEAVES = [("researcher", "researcher"), ("analyst", "analyzer"), ("writer", "writer")]


async def _seed(session: AsyncSession) -> tuple[UUID, UUID, UUID, UUID]:
    """Insert workspace + cell + master archetype + 3 leaves + running parent task.

    Returns ``(cell_id, parent_task_id, user_id, master_archetype_id)``.
    """
    workspace_id, cell_id, user_id, parent_id = uuid4(), uuid4(), uuid4(), uuid4()
    master_arc_id = uuid4()
    suffix = str(workspace_id)[:8]
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(workspace_id), "slug": f"master-{suffix}", "name": "Master Billing WS"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name, "
            " vertical_template_slug) VALUES (:id, :ws, 'default', 'Default', :v)"
        ),
        {"id": str(cell_id), "ws": str(workspace_id), "v": _VERTICAL},
    )
    # Master archetype under the vertical (role_category='master', agents_0004).
    await session.execute(
        text(
            "INSERT INTO agents.agent_archetypes "
            "(id, slug, vertical_slug, display_name, role_category, prompt_version, "
            " model_provider_slug, model_name) "
            "VALUES (:id, 'master', :v, 'Master', 'master', 'v1', 'deepseek', 'deepseek-chat')"
        ),
        {"id": str(master_arc_id), "v": _VERTICAL},
    )
    for slug, role_category in _LEAVES:
        await session.execute(
            text(
                "INSERT INTO agents.agent_archetypes "
                "(id, slug, vertical_slug, display_name, role_category, prompt_version, "
                " model_provider_slug, model_name) "
                "VALUES (:id, :slug, 'horizontal', :dn, :rc, 'v1', 'deepseek', 'deepseek-chat')"
            ),
            {"id": str(uuid4()), "slug": slug, "dn": slug.title(), "rc": role_category},
        )
    await session.execute(
        text(
            "INSERT INTO tasks.tasks (id, cell_id, initiated_by_user_id, title, description, status) "
            "VALUES (:id, :cell, :user, 'master parent', '', 'running')"
        ),
        {"id": str(parent_id), "cell": str(cell_id), "user": str(user_id)},
    )
    for guc, val in (
        ("app.current_user_id", user_id),
        ("app.current_cell_id", cell_id),
        ("app.current_workspace_id", workspace_id),
    ):
        await session.execute(text("SELECT set_config(:k, :v, true)"), {"k": guc, "v": str(val)})
    return cell_id, parent_id, user_id, master_arc_id


def _master_billing(cell_id: UUID, parent_id: UUID, user_id: UUID, *, phase: str, idx: int):
    return MasterCallBilling(
        parent_task_id=parent_id,
        cell_id=cell_id,
        user_id=user_id,
        vertical_tag=_VERTICAL,
        phase=phase,
        step_index=idx,
        provider_slug=_PROVIDER,
        model_name=_MODEL,
        input_tokens=800,
        output_tokens=400,
        latency_ms=33,
    )


async def test_master_call_step_resolves_master_archetype_and_bills(
    db_session_committed: AsyncSession,
) -> None:
    session = db_session_committed
    cell_id, parent_id, user_id, master_arc_id = await _seed(session)

    # Master plan (step 0) + synthesis (step 4) bracket the 3 leaf delegations.
    plan_cost = await record_master_call_step(
        session, _master_billing(cell_id, parent_id, user_id, phase="plan", idx=0)
    )
    for i, (slug, _rc) in enumerate(_LEAVES, start=1):
        await record_delegation_step(
            session,
            StepBilling(
                parent_task_id=parent_id,
                cell_id=cell_id,
                user_id=user_id,
                step_index=i,
                target_agent_slug=slug,
                provider_slug=_PROVIDER,
                model_name=_MODEL,
                input_tokens=1000,
                output_tokens=2000,
                latency_ms=42,
            ),
        )
    synth_cost = await record_master_call_step(
        session, _master_billing(cell_id, parent_id, user_id, phase="synthesis", idx=4)
    )

    assert plan_cost > 0 and synth_cost > 0  # real ledger pricing, not estimate

    # AC-W1-3.3: the 2 Master steps are typed 'llm_call' and FK the MASTER archetype
    # of this vertical (not a leaf), proving vertical-scoped resolution.
    master_steps = (
        await session.execute(
            text(
                "SELECT step_index, agent_archetype_id FROM tasks.task_steps "
                "WHERE task_id = :t AND step_type = 'llm_call' ORDER BY step_index"
            ),
            {"t": str(parent_id)},
        )
    ).all()
    assert [r[0] for r in master_steps] == [0, 4]
    assert all(str(r[1]) == str(master_arc_id) for r in master_steps)

    # AC-W1-3.4: step-sum authority = 2 master llm_call + 3 delegation, no double-count.
    counts = (
        await session.execute(
            text(
                "SELECT step_type, count(*) FROM tasks.task_steps WHERE task_id = :t "
                "GROUP BY step_type ORDER BY step_type"
            ),
            {"t": str(parent_id)},
        )
    ).all()
    assert dict(counts) == {"delegation": 3, "llm_call": 2}
    steps_sum = (
        await session.execute(
            text("SELECT sum(cost_credits) FROM tasks.task_steps WHERE task_id = :t"),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    leaf_sum = (
        await session.execute(
            text(
                "SELECT sum(cost_credits) FROM tasks.task_steps "
                "WHERE task_id = :t AND step_type = 'delegation'"
            ),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    # The step-sum the orchestrator stamps as task.total_cost_credits = the two
    # Master calls + the leaf delegations, each counted exactly once.
    assert steps_sum == plan_cost + synth_cost + leaf_sum
    assert leaf_sum > 0
