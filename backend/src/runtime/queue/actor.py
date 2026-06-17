"""Dramatiq dispatch actor — runs a task orchestration off the request thread.

``POST /tasks/{id}/run`` enqueues ``dispatch_task_actor.send(task_id, user_id)``
and returns 202 in <1s (AC-W1-16a); the worker process runs the actual
researcher→analyst→writer orchestration and streams its SSE ledger through the
Redis-Streams publisher (AC-W1-1) so the web tier's ``/stream`` sees it.

The worker has no FastAPI ``app.state``, so it builds its own dependencies:
the LLMRouter (via the shared ``build_llm_router`` seam), the SSE publisher
(Redis backend), and its own RLS-scoped DB session. It resolves the tenant GUCs
itself (no request middleware) via the same SECURITY-DEFINER membership lookup
the request path uses, and guards on ``status == 'queued'`` so a redelivered
message is a no-op (never double-runs / double-charges).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import dramatiq
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src._shared.config import get_settings
from src._shared.db.redis import get_redis_client
from src._shared.db.rls import set_tenant_context
from src._shared.middleware.tenant_context import _resolve_tenant_ids
from src.llm_gateway.factory import build_llm_router
from src.llm_gateway.services.router_service import LLMRouter
from src.mcp.tools.rate_limit import ToolRateLimiter
from src.runtime.dispatch import dispatch_task
from src.runtime.queue import broker  # noqa: F401 — installs the broker before @actor binds
from src.runtime.sse_publisher import SSEPublisher, get_sse_publisher
from src.tasks.models import Task
from src.tasks.services.task_service import TaskService

logger = structlog.get_logger(__name__)

# Injection seams (defaults are the production paths; tests pass fakes so the
# guard + wiring stay deterministic without a real DB).
TenantResolver = Callable[..., Awaitable[tuple[UUID, UUID]]]
TaskLoader = Callable[[AsyncSession, UUID], Awaitable[Task]]
DispatchFn = Callable[..., Awaitable[dict[str, Any]]]


async def _load_task(session: AsyncSession, task_id: UUID) -> Task:
    return await TaskService(session).get_task(task_id)


async def run_task_dispatch(
    *,
    session: AsyncSession,
    task_id: UUID,
    user_id: UUID,
    router: LLMRouter,
    publisher: SSEPublisher,
    resolve_tenant: TenantResolver = _resolve_tenant_ids,
    load_task: TaskLoader = _load_task,
    dispatch: DispatchFn = dispatch_task,
    tool_rate_limiter: ToolRateLimiter | None = None,
) -> bool:
    """Run a queued task's orchestration under RLS. Returns True if it ran,
    False if it was skipped as already-dispatched (idempotency / redelivery).

    Owns its commit: on success commits after dispatch; on failure commits the
    orchestrator's failed-state write (so the DB and the SSE ledger agree) then
    re-raises. Because the guard keys on status=='queued', a retry after a
    committed failure is a no-op — the intended "don't re-run" posture.
    """
    workspace_id, cell_id = await resolve_tenant(session=session, user_id=user_id)
    async with set_tenant_context(
        session, workspace_id=workspace_id, cell_id=cell_id, user_id=user_id
    ):
        task = await load_task(session, task_id)
        if task.status != "queued":
            logger.info(
                "runtime.dispatch.actor.skip_non_queued",
                task_id=str(task_id),
                status=task.status,
            )
            return False
        # P1-B fix: claim the task with a COMMITTED transition out of 'queued'
        # BEFORE the long LLM orchestration. The orchestrator flips status to
        # 'running' in-memory but never commits until the work finishes, so a
        # worker crash / time_limit / redelivery mid-run rolls the uncommitted
        # 'running' back to 'queued' and the queued-guard above passes again —
        # re-running the whole paid researcher→analyst→writer chain (and
        # duplicating child Task rows). Committing 'running' here means a
        # redelivered message sees a non-queued row and short-circuits.
        task.status = "running"
        await session.commit()
        try:
            await dispatch(
                task=task,
                session=session,
                llm_router=router,
                sse_publisher=publisher,
                # AC-W1-19: throttle the Researcher's native web_search loop via
                # Redis. dispatch_task only uses it on the DeepSeek (native
                # tool-call) path; the scripted-failover path ignores it.
                tool_rate_limiter=tool_rate_limiter,
            )
        except Exception:
            logger.exception("runtime.dispatch.actor.failed", task_id=str(task_id))
            # Persist the orchestrator's failed-state write before re-raising
            # (mirrors the old inline endpoint's F-CR-2 fix).
            await session.commit()
            raise
        await session.commit()
        return True


async def _run_dispatch(task_id: UUID, user_id: UUID) -> None:
    """Worker-side entry: build deps + a fresh NullPool engine (each asyncio.run
    gets its own event loop, so a process-cached pooled engine would bind
    connections to a dead loop) and run the dispatch."""
    settings = get_settings()
    bundle = build_llm_router(settings)
    publisher = get_sse_publisher()
    tool_rate_limiter = ToolRateLimiter(get_redis_client())
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
        async with maker() as session:
            await run_task_dispatch(
                session=session,
                task_id=task_id,
                user_id=user_id,
                router=bundle.router,
                publisher=publisher,
                tool_rate_limiter=tool_rate_limiter,
            )
    finally:
        await engine.dispose()


@dramatiq.actor(max_retries=3, time_limit=300_000, queue_name="dispatch")
def dispatch_task_actor(task_id: str, user_id: str) -> None:
    """Sync Dramatiq actor wrapping the async dispatch. Runs in a worker thread;
    asyncio.run gives it a fresh loop per message."""
    import asyncio

    asyncio.run(_run_dispatch(UUID(task_id), UUID(user_id)))
