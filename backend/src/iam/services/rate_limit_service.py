"""Redis-backed sliding-window rate limit.

Lua script ensures INCR + EXPIRE are atomic on the first hit so the
window starts at hit #1 and doesn't reset on subsequent ones.

Per-scope thresholds (Q6 decision in session-context plan):
    login                  → 5 / 15 min (ip, email)
    register               → 5 / 15 min (ip, email)
    forgot-password        → 3 / 15 min (ip, email)   anti-spam
    resend-verification    → 3 / 15 min (ip, email)   anti-spam
    refresh                → 30 / 1 min (ip)
    verify-email           → 10 / 1 min (ip)
    reset-password         → 10 / 1 min (ip)
    magic-link (Phase 01.8)→ 3 / 15 min (ip, email)  anti-spam
    totp      (Phase 01.8) → 5 / 5 min (ip)           brute-force cap

Anti-enumeration note (invariant 9): the counter increments regardless of
whether the email exists. So a 429 from forgot/resend does not signal
"account exists" — only that this (ip,email) tuple has hit the threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, cast

from redis.asyncio import Redis

# Lua: atomically INCR a key and set EXPIRE only on first hit (NX TTL preserve).
_ATOMIC_INCR_EXPIRE_LUA: Final = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {n, ttl}
"""


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    threshold: int
    window_seconds: int


# Per-scope policy (Q6). Tweaking these is a contract change — review with
# security before adjusting.
SCOPE_POLICY: Final[dict[str, RateLimitConfig]] = {
    "login": RateLimitConfig(threshold=5, window_seconds=900),
    "register": RateLimitConfig(threshold=5, window_seconds=900),
    "forgot": RateLimitConfig(threshold=3, window_seconds=900),
    "resend": RateLimitConfig(threshold=3, window_seconds=900),
    "refresh": RateLimitConfig(threshold=30, window_seconds=60),
    "verify": RateLimitConfig(threshold=10, window_seconds=60),
    "reset": RateLimitConfig(threshold=10, window_seconds=60),
    # Phase 01.8 — passwordless login link request: anti-spam like forgot.
    "magic_link": RateLimitConfig(threshold=3, window_seconds=900),
    # Phase 01.8 — TOTP second-factor verify: cap brute-force of the 6-digit
    # code within a login attempt (5 tries / 5 min per ip).
    "totp": RateLimitConfig(threshold=5, window_seconds=300),
}


@dataclass(frozen=True, slots=True)
class RateLimitVerdict:
    allowed: bool
    remaining: int  # attempts left in the current window (>= 0)
    retry_after: int  # seconds until window resets


class RateLimitService:
    """Redis-backed atomic counter with per-scope policy."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check_and_increment(
        self,
        scope: str,
        ip: str,
        email: str | None = None,
    ) -> RateLimitVerdict:
        """Increment the (scope, ip, email|none) counter atomically.

        scope MUST be one of SCOPE_POLICY keys. email is normalised
        (lower-case, stripped). When email is None the key is ip-only.
        """
        try:
            policy = SCOPE_POLICY[scope]
        except KeyError as exc:
            raise ValueError(f"unknown rate-limit scope: {scope!r}") from exc

        key = self._build_key(scope, ip, email)
        raw = await cast(
            Any,
            self._redis.eval(
                _ATOMIC_INCR_EXPIRE_LUA,
                1,
                key,
                str(policy.window_seconds),
            ),
        )
        # eval returns [count, ttl_seconds]
        count = int(raw[0])
        ttl = max(int(raw[1]), 0)

        return RateLimitVerdict(
            allowed=count <= policy.threshold,
            remaining=max(policy.threshold - count, 0),
            retry_after=ttl,
        )

    @staticmethod
    def _build_key(scope: str, ip: str, email: str | None) -> str:
        if email is None:
            return f"ratelimit:{scope}:{ip}"
        normalized = email.strip().lower()
        return f"ratelimit:{scope}:{ip}:{normalized}"
