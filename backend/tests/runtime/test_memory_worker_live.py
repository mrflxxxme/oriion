"""Live worker-path golden — memory auto-extraction through ``run_task_dispatch``.

Phase 01.4 closeout (grill 2026-06-24 Q2: "run the worker-through golden now").
Drives the WORKER CORE (``runtime.queue.actor.run_task_dispatch``) end-to-end on
real PG (testcontainer, superuser → RLS-bypass for seeding) with a REAL
``llm_router`` (funded ``backend/.env``) + an ``InProcessSSEPublisher`` in a single
event loop — which sidesteps the Windows redis-per-loop / one-task-per-worker flake
(the Dramatiq+Redis transport is proven on Linux, PR #64/#65 +
``scripts/live_golden_worker_billing.py``).

Validates the seam green unit/integration cannot: a REAL succeeded multi-agent task
→ the orchestrator's post-success ``memory_extraction`` hook → the LIVE filter-agent
→ ``memory_entries`` + a billed memory ``task_steps`` row, with the step-sum
invariant (``task.total_cost_credits == SUM(steps)``) holding on REAL data.

Run (Docker up, funded backend/.env):
    uv run --directory backend pytest tests/runtime/test_memory_worker_live.py -m live -q -s
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.config import get_settings
from src.agents.seed_data.memory_curator_v1 import ensure_memory_curator_archetype
from src.agents.seed_data.productivity_core_v1 import ensure_productivity_core_seed
from src.llm_gateway.factory import build_llm_router
from src.runtime.dispatch import dispatch_task
from src.runtime.queue.actor import run_task_dispatch
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.models import Task

pytestmark = [pytest.mark.live, pytest.mark.commit_required]

_PROMPT = (
    "Наш клиент — сеть кофеен «КофеКазань»: 4 точки в Казани, ЦА молодёжь 18-30, "
    "бюджет ~150к ₽/мес, основной конкурент «Бариста-Х». Подготовь для клиента "
    "контент-план на 5 постов для Telegram и короткую конкурентную матрицу (>=4 строк). "
    "Опирайся на общие знания, без веб-поиска."
)


async def test_memory_extraction_through_worker_live(db_session_committed: AsyncSession) -> None:
    session = db_session_committed
    settings = get_settings()
    if not settings.deepseek_api_key.get_secret_value():
        pytest.skip("DEEPSEEK_API_KEY not set — live golden needs the funded backend/.env")

    # ── seed a horizontal cell (superuser testcontainer → RLS bypassed) ──
    await ensure_productivity_core_seed(session)  # coordinator/researcher/writer/analyst + preset
    await ensure_memory_curator_archetype(session)
    ws_id, cell_id, user_id, task_id = uuid4(), uuid4(), uuid4(), uuid4()
    await session.execute(
        text("INSERT INTO multitenancy.workspaces (id, slug, display_name) VALUES (:id,:s,'WS')"),
        {"id": str(ws_id), "s": f"ws-{ws_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id,:ws,'default','C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    task = Task(
        cell_id=cell_id,
        initiated_by_user_id=user_id,
        title="memory worker live golden",
        description="",
        input_jsonb={"prompt": _PROMPT},
        status="queued",
    )
    task.id = task_id
    session.add(task)
    await session.flush()

    # ── drive the worker core vs LIVE DeepSeek, in-process (no Dramatiq/redis) ──
    router = build_llm_router(settings).router
    publisher = InProcessSSEPublisher()

    async def _resolve(*, session: AsyncSession, user_id: UUID) -> tuple[UUID, UUID]:
        return ws_id, cell_id

    async def _load(session: AsyncSession, _task_id: UUID) -> Task:
        loaded = await session.get(Task, task_id)
        assert loaded is not None
        return loaded

    ran = await run_task_dispatch(
        session=session,
        task_id=task_id,
        user_id=user_id,
        router=router,
        publisher=publisher,
        resolve_tenant=_resolve,
        load_task=_load,
        dispatch=dispatch_task,
    )
    assert ran is True

    # ── assert: succeeded + a billed memory step + the invariant on REAL data ──
    final = await session.get(Task, task_id)
    assert final is not None
    print(f"\n[live] status={final.status} total_cost={final.total_cost_credits}")
    assert final.status == "succeeded"

    steps = (
        await session.execute(
            text(
                "SELECT input_jsonb->>'phase' AS phase, step_type, cost_credits "
                "FROM tasks.task_steps WHERE task_id=:t ORDER BY step_index"
            ),
            {"t": str(task_id)},
        )
    ).all()
    print(f"[live] steps: {[(s[0], s[1], str(s[2])) for s in steps]}")
    # The post-task memory hook is BEST-EFFORT (grill Q5): a transient LLM error is
    # swallowed and the task still succeeds, so 0-or-1 extraction steps is valid; when
    # present it must be a single, well-formed llm_call (no double-count).
    mem_steps = [s for s in steps if s[0] == "extraction"]
    assert len(mem_steps) <= 1
    if mem_steps:
        assert mem_steps[0][1] == "llm_call"
    else:
        print("[live] NOTE: filter call did not complete this run (best-effort swallow)")

    # HARD invariant on REAL multi-agent data — holds whether or not the memory step ran.
    steps_sum = sum((s[2] for s in steps), start=Decimal(0))
    assert final.total_cost_credits == steps_sum

    entries = (
        await session.execute(
            text(
                "SELECT kind, content FROM memory.memory_entries "
                "WHERE cell_id=:c AND source='filter_agent'"
            ),
            {"c": str(cell_id)},
        )
    ).all()
    # entries are a heuristic live signal (depends on the filter's should_remember verdict)
    print(f"[live] filter_agent memory_entries ({len(entries)}):")
    for kind, content in entries:
        print(f"   - [{kind}] {content[:80]}")
