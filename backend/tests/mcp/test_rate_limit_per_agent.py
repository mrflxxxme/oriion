"""Unit: ToolRateLimiter — per-agent INCR+EXPIRE atomic limiter."""

from __future__ import annotations

import pytest
from src.mcp.tools.rate_limit import ToolRateLimiter, ToolRateLimitVerdict


@pytest.mark.asyncio
async def test_under_limit_returns_true(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    for _ in range(10):
        allowed = await limiter.check(
            agent_id="agent-1",
            tool_name="read_url",
            limit=10,
            window_seconds=60,
        )
        assert allowed is True


@pytest.mark.asyncio
async def test_over_limit_returns_false(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    for _ in range(10):
        await limiter.check(
            agent_id="agent-1",
            tool_name="read_url",
            limit=10,
            window_seconds=60,
        )
    allowed = await limiter.check(
        agent_id="agent-1",
        tool_name="read_url",
        limit=10,
        window_seconds=60,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_per_agent_isolation(fake_redis: object) -> None:
    """Two distinct agents must have independent counters."""
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    for _ in range(10):
        await limiter.check(
            agent_id="agent-1",
            tool_name="read_url",
            limit=10,
            window_seconds=60,
        )
    other = await limiter.check(
        agent_id="agent-2",
        tool_name="read_url",
        limit=10,
        window_seconds=60,
    )
    assert other is True


@pytest.mark.asyncio
async def test_per_tool_isolation(fake_redis: object) -> None:
    """Two tools must have independent counters per agent."""
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    for _ in range(10):
        await limiter.check(
            agent_id="agent-1",
            tool_name="read_url",
            limit=10,
            window_seconds=60,
        )
    other = await limiter.check(
        agent_id="agent-1",
        tool_name="web_search",
        limit=10,
        window_seconds=60,
    )
    assert other is True


@pytest.mark.asyncio
async def test_check_detailed_reports_remaining_and_retry_after(
    fake_redis: object,
) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    v1 = await limiter.check_detailed(agent_id="a", tool_name="t", limit=3, window_seconds=60)
    assert isinstance(v1, ToolRateLimitVerdict)
    assert v1.allowed is True
    assert v1.remaining == 2

    await limiter.check_detailed(agent_id="a", tool_name="t", limit=3, window_seconds=60)
    await limiter.check_detailed(agent_id="a", tool_name="t", limit=3, window_seconds=60)
    blocked = await limiter.check_detailed(agent_id="a", tool_name="t", limit=3, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after >= 0


@pytest.mark.asyncio
async def test_zero_limit_rejected(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        await limiter.check(agent_id="a", tool_name="t", limit=0, window_seconds=60)


@pytest.mark.asyncio
async def test_zero_window_rejected(fake_redis: object) -> None:
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        await limiter.check(agent_id="a", tool_name="t", limit=10, window_seconds=0)


@pytest.mark.asyncio
async def test_key_normalisation_case_insensitive(fake_redis: object) -> None:
    """Casing differences MUST NOT bypass the limit."""
    limiter = ToolRateLimiter(redis=fake_redis)  # type: ignore[arg-type]
    await limiter.check(agent_id="Agent-1", tool_name="Read_URL", limit=2, window_seconds=60)
    await limiter.check(agent_id="agent-1", tool_name="read_url", limit=2, window_seconds=60)
    blocked = await limiter.check(
        agent_id="AGENT-1", tool_name="READ_URL", limit=2, window_seconds=60
    )
    assert blocked is False
