"""dispatch actor — broker enqueue + run_task_dispatch guard/commit semantics.

No real Redis, DB, or LLM: the StubBroker (selected via DRAMATIQ_TESTING in the
root conftest) covers enqueue; run_task_dispatch is exercised with injected fakes
so the idempotency guard + commit ordering stay deterministic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import dramatiq
import pytest
from src.runtime.queue.actor import dispatch_task_actor, run_task_dispatch


class _FakeSession:
    """Async session stub: swallows set_config executes, counts commits."""

    def __init__(self) -> None:
        self.commits = 0

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


async def _resolve_fixed(*, session: Any, user_id: UUID) -> tuple[UUID, UUID]:
    return uuid4(), uuid4()


def _task(status: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), status=status, cell_id=uuid4())


# ── broker enqueue (StubBroker) ───────────────────────────────────────────


def test_actor_registered_and_send_enqueues() -> None:
    broker = dramatiq.get_broker()
    broker.flush_all()
    assert isinstance(dispatch_task_actor, dramatiq.Actor)
    dispatch_task_actor.send(str(uuid4()), str(uuid4()))
    assert broker.queues["dispatch"].qsize() == 1


# ── run_task_dispatch: queued → runs ──────────────────────────────────────


@pytest.mark.asyncio
async def test_runs_and_commits_when_queued() -> None:
    session = _FakeSession()
    calls: list[str] = []

    async def fake_dispatch(**kwargs: Any) -> dict[str, Any]:
        calls.append("dispatch")
        return {}

    ran = await run_task_dispatch(
        session=session,  # type: ignore[arg-type]
        task_id=uuid4(),
        user_id=uuid4(),
        router=object(),  # type: ignore[arg-type]
        publisher=object(),  # type: ignore[arg-type]
        resolve_tenant=_resolve_fixed,
        load_task=lambda _s, _t: _ready(_task("queued")),
        dispatch=fake_dispatch,
    )

    assert ran is True
    assert calls == ["dispatch"]
    assert session.commits == 1


# ── run_task_dispatch: non-queued → idempotent skip ───────────────────────


@pytest.mark.asyncio
async def test_skips_when_not_queued() -> None:
    session = _FakeSession()
    calls: list[str] = []

    async def fake_dispatch(**kwargs: Any) -> dict[str, Any]:
        calls.append("dispatch")
        return {}

    ran = await run_task_dispatch(
        session=session,  # type: ignore[arg-type]
        task_id=uuid4(),
        user_id=uuid4(),
        router=object(),  # type: ignore[arg-type]
        publisher=object(),  # type: ignore[arg-type]
        resolve_tenant=_resolve_fixed,
        load_task=lambda _s, _t: _ready(_task("running")),
        dispatch=fake_dispatch,
    )

    assert ran is False
    assert calls == []  # redelivery / double-dispatch is a no-op
    assert session.commits == 0


# ── run_task_dispatch: failure commits failed-state + re-raises ────────────


@pytest.mark.asyncio
async def test_commits_failed_state_and_reraises() -> None:
    session = _FakeSession()

    async def boom(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("provider exploded")

    with pytest.raises(RuntimeError, match="provider exploded"):
        await run_task_dispatch(
            session=session,  # type: ignore[arg-type]
            task_id=uuid4(),
            user_id=uuid4(),
            router=object(),  # type: ignore[arg-type]
            publisher=object(),  # type: ignore[arg-type]
            resolve_tenant=_resolve_fixed,
            load_task=lambda _s, _t: _ready(_task("queued")),
            dispatch=boom,
        )
    assert session.commits == 1  # failed-state persisted before re-raise


async def _ready(value: Any) -> Any:
    """Wrap a value in an awaitable so a lambda can stand in for an async loader."""
    return value
