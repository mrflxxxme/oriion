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
    # P1-B: a committed 'running' claim BEFORE dispatch + the post-dispatch
    # commit = 2 commits total.
    assert session.commits == 2


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


# ── run_task_dispatch: redelivery short-circuits after committed claim (P1-B) ──


@pytest.mark.asyncio
async def test_redelivery_runs_dispatch_only_once() -> None:
    """P1-B: a worker crash/time_limit/redelivery must NOT re-run the paid
    orchestration. The committed 'running' claim before dispatch means the
    second (redelivered) invocation sees a non-queued row and short-circuits,
    so the dispatch body fires exactly once.

    The shared ``task`` object models the persisted row: the first call commits
    status='running' on it, the second call (same row) reads 'running' and skips.
    """
    session = _FakeSession()
    task = _task("queued")  # shared row — claim persists across redeliveries
    calls: list[str] = []

    async def fake_dispatch(**kwargs: Any) -> dict[str, Any]:
        calls.append("dispatch")
        return {}

    common = {
        "session": session,
        "task_id": task.id,
        "user_id": uuid4(),
        "router": object(),
        "publisher": object(),
        "resolve_tenant": _resolve_fixed,
        "load_task": lambda _s, _t: _ready(task),
        "dispatch": fake_dispatch,
    }

    first = await run_task_dispatch(**common)  # type: ignore[arg-type]
    assert task.status == "running"  # claim committed out of 'queued'
    second = await run_task_dispatch(**common)  # type: ignore[arg-type]  # redelivery

    assert first is True
    assert second is False  # redelivery is a no-op
    assert calls == ["dispatch"]  # orchestration body ran exactly ONCE


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
    # P1-B: 'running' claim committed before dispatch (1) + failed-state
    # persisted before re-raise (1) = 2.
    assert session.commits == 2


async def _ready(value: Any) -> Any:
    """Wrap a value in an awaitable so a lambda can stand in for an async loader."""
    return value
