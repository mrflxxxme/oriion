"""Focused live proof of the Phase 01.3 per-day cap (R-04) on the worker path.

Run against a FRESHLY-started worker so the capped task is the worker's FIRST
dispatched message (in the local-Windows setup a worker reliably processes one
dispatch task per process — a 2nd stalls before task.started, a separate
worker-infra finding; this script isolates the cap assertion from it).

register -> seed a 200-credit debit (>= Trial per-day cap 150) BEFORE any task
-> create + run ONE task -> the worker's admission gate raises DailyQuotaExceeded
-> task ends 'failed' with ~0 cost (blocked before any LLM call).

Run (against the local stack, SSE_BACKEND=redis or inprocess):
  ... DATABASE_URL=...:55432 REDIS_URL=...:56379 \
      uv run --directory backend python scripts/live_cap_check.py
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src._shared.config import get_settings

BASE = "http://127.0.0.1:8001/api/v1"
_PW = "very-strong-password-123"


async def _poll(c: httpx.AsyncClient, h: dict[str, str], cell: str, tid: str) -> dict[str, Any]:
    deadline = time.monotonic() + 120.0
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = (await c.get(f"/cells/{cell}/tasks/{tid}", headers=h)).json()
        if last.get("status") in ("succeeded", "failed", "cancelled"):
            return last
        await asyncio.sleep(2.0)
    return last


async def main() -> int:
    settings = get_settings()
    email = f"cap-{uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as c:
        r = await c.post(
            "/auth/register",
            json={"email": email, "password": _PW, "consent_pdn": True, "display_name": "C"},
        )
        reg = r.json()
        cell_id, workspace_id = reg["cell_id"], reg["workspace_id"]
        tok = (await c.post("/auth/login", json={"email": email, "password": _PW})).json()[
            "access_token"
        ]
        h = {"Authorization": f"Bearer {tok}"}

        # Seed daily usage over the Trial per-day cap (150) BEFORE running a task.
        engine = create_async_engine(settings.database_url.get_secret_value())
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO billing.credit_transactions "
                        "(cell_id, workspace_id, transaction_type, amount_rub, amount_credits, "
                        " balance_after_credits, tokens_input, tokens_output) "
                        "VALUES (:c, :w, 'debit', 200, 200, 0, 0, 0)"
                    ),
                    {"c": cell_id, "w": workspace_id},
                )
        finally:
            await engine.dispose()

        r = await c.post(
            f"/cells/{cell_id}/tasks",
            headers=h,
            json={"title": "cap", "description": "blocked", "prompt": "сделай бриф"},
        )
        tid = r.json()["id"]
        await c.post(f"/cells/{cell_id}/tasks/{tid}/run", headers=h)
        task = await _poll(c, h, cell_id, tid)
        status = task.get("status")
        cost = Decimal(str(task.get("total_cost_credits", "0")))
        print(f"capped task: status={status} cost={cost}")
        ok = status == "failed" and cost == Decimal(0)
        print(
            f"[{'PASS' if ok else 'FAIL'}] per-day cap blocks the task at worker admission (R-04)"
        )
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
