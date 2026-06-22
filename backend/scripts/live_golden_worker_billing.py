"""Worker-path live golden — Dramatiq + RLS-billing persistence + Phase 01.3.

Drives the REAL async worker tract end-to-end over HTTP against a running
backend (:8001) + Dramatiq worker + Postgres + Redis (the part green
unit/integration tests cannot cover — per `live-golden-async-dispatch-findings`):

  1. register -> the 01.3 Trial grant fires (assert balance == 500);
  2. create + `POST /run` a task -> 202 in <1s (AC-W1-16a dispatch latency);
  3. the Dramatiq worker orchestrates off-request -> task `succeeded`;
     assert `0 < total_cost_credits <= 50` (per-task cap, real billing);
  4. RLS-billing persistence: balance dropped + the ledger has debit rows that
     reconcile with the period usage.

The per-day cap (R-04) is proven by the focused `live_cap_check.py` (it must be
the worker's first message — see the worker 2nd-message note in that file).

Run (against the local stack, funded DeepSeek in backend/.env):
  ... DATABASE_URL=...:55432 REDIS_URL=...:56379 SSE_BACKEND=inprocess \
      uv run --directory backend python scripts/live_golden_worker_billing.py

Prints a PASS/FAIL summary; exit 0 iff every gate passes.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

BASE = "http://127.0.0.1:8001/api/v1"
_PASSWORD = "very-strong-password-123"  # noqa: S105 — ephemeral test-user password, not a secret
_TASK_TIMEOUT_S = 300.0
_POLL_S = 3.0


def _gate(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


async def _poll_terminal(
    client: httpx.AsyncClient, headers: dict[str, str], cell_id: str, task_id: str
) -> dict[str, Any]:
    deadline = time.monotonic() + _TASK_TIMEOUT_S
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        r = await client.get(f"/cells/{cell_id}/tasks/{task_id}", headers=headers)
        last = r.json()
        if last.get("status") in ("succeeded", "failed", "cancelled"):
            return last
        await asyncio.sleep(_POLL_S)
    return last


async def main() -> int:
    results: list[tuple[str, bool, str]] = []
    email = f"golden-worker-{uuid4().hex[:8]}@example.com"

    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as c:
        # ── 1. register -> Trial grant (01.3) ─────────────────────────────
        print("=" * 70)
        print("[1] register -> Trial grant")
        r = await c.post(
            "/auth/register",
            json={"email": email, "password": _PASSWORD, "consent_pdn": True, "display_name": "G"},
        )
        if r.status_code != 201:
            print(f"FATAL: register {r.status_code}: {r.text}")
            return 2
        cell_id = r.json()["cell_id"]
        r = await c.post("/auth/login", json={"email": email, "password": _PASSWORD})
        if r.status_code != 200:
            print(f"FATAL: login {r.status_code}: {r.text}")
            return 2
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        bal = (await c.get("/billing/balance", headers=headers)).json()
        _gate(
            results,
            "register grants Trial 500",
            bal.get("balance_credits") == "500.0000",
            str(bal.get("balance_credits")),
        )
        sub = (await c.get("/billing/subscription", headers=headers)).json()
        _gate(
            results,
            "subscription = trial",
            sub.get("plan_slug") == "trial" and sub.get("status") == "trial",
            f"{sub.get('plan_slug')}/{sub.get('status')}",
        )

        # ── 2. create + dispatch a task (worker-path) ─────────────────────
        print("=" * 70)
        print("[2] create + POST /run (Dramatiq dispatch)")
        r = await c.post(
            f"/cells/{cell_id}/tasks",
            headers=headers,
            json={
                "title": "worker-path golden",
                "description": "live billing E2E",
                # Rich multi-deliverable brief (mirrors demo_market_brief DEMO_PROMPT)
                # so the Coordinator delegates to researcher/analyst/writer → real
                # leaf billing fires (a trivial prompt yields 0 delegations / 0 cost).
                "prompt": (
                    "Запускаем платформу AI-команд для SMB в РФ. Подготовь маркетинговый пакет: "
                    "(1) market brief на русском (контекст рынка, ICP, конкуренты, позиционирование, "
                    "риски, next steps); (2) конкурентную матрицу ≥5 строк × ≥4 колонки; "
                    "(3) контент-план на 10 постов (Telegram + vc.ru)."
                ),
            },
        )
        task_id = r.json()["id"]
        t0 = time.monotonic()
        r = await c.post(f"/cells/{cell_id}/tasks/{task_id}/run", headers=headers)
        dispatch_s = time.monotonic() - t0
        _gate(
            results,
            "dispatch 202 in <1s (AC-W1-16a)",
            r.status_code == 202 and dispatch_s < 1.0,
            f"{r.status_code}, {dispatch_s:.3f}s",
        )

        # ── 3. worker orchestrates off-request -> terminal + real billing ──
        print("=" * 70)
        print("[3] worker orchestration (polling task)…")
        task = await _poll_terminal(c, headers, cell_id, task_id)
        status = task.get("status")
        cost = Decimal(str(task.get("total_cost_credits", "0")))
        print(
            f"    status={status} cost={cost} in_tok={task.get('total_input_tokens')} out_tok={task.get('total_output_tokens')}"
        )
        _gate(
            results, "task reached 'succeeded' (worker tract)", status == "succeeded", str(status)
        )
        _gate(
            results,
            "0 < total_cost_credits <= 50 (per-task cap, real billing)",
            Decimal(0) < cost <= Decimal(50),
            str(cost),
        )

        # ── 4. RLS-billing persistence ─────────────────────────────────────
        print("=" * 70)
        print("[4] RLS-billing persistence")
        bal2 = (await c.get("/billing/balance", headers=headers)).json()
        _gate(
            results,
            "balance dropped below 500 after the run",
            Decimal(str(bal2["balance_credits"])) < Decimal(500),
            str(bal2["balance_credits"]),
        )
        txs = (await c.get("/billing/transactions", headers=headers)).json()
        debits = [t for t in txs if t["transaction_type"] == "debit"]
        _gate(
            results,
            "ledger has >=1 debit row (managed usage persisted)",
            len(debits) >= 1,
            f"{len(debits)} debit(s)",
        )
        period_usage = Decimal(str(bal2.get("period_usage_credits", "0")))
        _gate(
            results,
            "period usage == 500 - balance (reconciles)",
            period_usage == Decimal(500) - Decimal(str(bal2["balance_credits"])),
            f"usage={period_usage}",
        )

    # ── summary ────────────────────────────────────────────────────────────
    print("=" * 70)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"SUMMARY: {passed}/{len(results)} gates passed")
    print(
        f"GATE (worker-path + RLS-billing + 01.3 trial/debit): {'PASS' if passed == len(results) else 'FAIL'}"
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
