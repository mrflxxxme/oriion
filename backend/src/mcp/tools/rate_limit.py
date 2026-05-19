"""Redis-backed per-agent tool rate limiter.

Mirrors `iam.services.rate_limit_service.RateLimitService` style — Lua
INCR + EXPIRE-on-first-hit so the window starts at hit #1 and the TTL is
not extended on later hits within the same window. Tool-level (vs auth-
level) lets us share Redis but keep separate key namespaces, so e.g. a
chatty user hammering `read_url` never affects the auth rate limiter.

Why a separate class (not reuse RateLimitService)?
    * Different policy axis — keyed on (agent_id, tool_name) instead of
      (scope, ip, email).
    * Limits are caller-supplied (per-tool config in the gateway / agent
      runtime), not baked into a fixed policy table. Auth limits MUST NOT
      drift; tool limits are tuned regularly.
    * Avoids growing iam's API surface with non-iam concerns.

Phase 00.4 § Task 14 calls out: `read_url` = 10/min, `web_search` = 30/min
per agent_id. Both are caller-configurable here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, cast

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

# Same Lua as iam.services.rate_limit_service — duplicated intentionally to
# keep the contexts independent. If a third place wants this, promote it to
# src._shared. The script returns [count, ttl_seconds].
_ATOMIC_INCR_EXPIRE_LUA: Final = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {n, ttl}
"""


@dataclass(frozen=True, slots=True)
class ToolRateLimitVerdict:
    """Result of a single rate-limit check.

    `allowed=False` means the counter exceeded `limit`; `retry_after` is
    the TTL of the existing window in seconds (>=0).
    """

    allowed: bool
    remaining: int
    retry_after: int


class ToolRateLimiter:
    """Per-agent rate limiter for built-in + MCP tool invocations."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(
        self,
        agent_id: str,
        tool_name: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """Atomically increment the (agent_id, tool_name) counter.

        Returns True if the call is allowed (count <= limit), False once
        the limit is exceeded within the window. The first call within a
        fresh window sets the EXPIRE.
        """
        verdict = await self.check_detailed(
            agent_id=agent_id,
            tool_name=tool_name,
            limit=limit,
            window_seconds=window_seconds,
        )
        return verdict.allowed

    async def check_detailed(
        self,
        agent_id: str,
        tool_name: str,
        limit: int,
        window_seconds: int,
    ) -> ToolRateLimitVerdict:
        """Same as `check` but also returns remaining + retry_after.

        Used by callers that want to surface `Retry-After` headers
        (eventual /api/mcp/tools/* endpoints).
        """
        if limit <= 0:
            raise ValueError("limit must be > 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        key = self._build_key(agent_id, tool_name)
        raw = await cast(
            Any,
            self._redis.eval(
                _ATOMIC_INCR_EXPIRE_LUA,
                1,
                key,
                str(window_seconds),
            ),
        )
        count = int(raw[0])
        ttl = max(int(raw[1]), 0)
        allowed = count <= limit
        if not allowed:
            logger.info(
                "mcp.tools.rate_limit.exceeded",
                agent_id=agent_id,
                tool_name=tool_name,
                count=count,
                limit=limit,
                retry_after=ttl,
            )
        return ToolRateLimitVerdict(
            allowed=allowed,
            remaining=max(limit - count, 0),
            retry_after=ttl,
        )

    @staticmethod
    def _build_key(agent_id: str, tool_name: str) -> str:
        # Normalised so callers can't accidentally bypass via case games.
        return f"mcp:ratelimit:{agent_id.strip().lower()}:{tool_name.strip().lower()}"
