"""Runnable demo: «Market & content brief» end-to-end against any deployed API.

Phase 00.5b Commit 7 SHIP, Phase 00.6 RUNS:
    * Ships in this PR but does NOT execute in CI (no live LLM keys).
    * Phase 00.6 staging deploy will run this with --runs N to collect
      gate evidence for AC8 (p95 ≤ 120s) + AC10 (cost ≤ 30¢) (D5 of
      gates/wave-0-to-1.md).

Usage::

    python -m scripts.demo_market_brief \\
        --api-base-url http://localhost:8000/api/v1 \\
        --jwt $env:DEV_JWT \\
        --runs 1 \\
        --output ./.tmp/demo-smoke/

The script:
    1. POSTs /cells/{cell_id}/tasks with the canonical demo prompt.
    2. Subscribes to /cells/{cell_id}/tasks/{task_id}/stream (SSE).
    3. Collects all events, computes wall-clock + cost stats.
    4. Validates artifact shapes per AC9 (brief ≥1500w, matrix ≥5x4,
       content-plan == 10 posts).
    5. Writes per-run JSON to `<output>/run_NNN.json` + summary.csv
       with p95 latency + cost columns for the cohort.

Exit codes:
    0 — all runs satisfied AC8 + AC9 + AC10
    1 — at least one run failed an AC threshold
    2 — transport / auth error (treat as infra failure, not AC fail)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

DEMO_PROMPT = (
    "Запускаем платформу AI-команд для SMB в РФ. "
    "Сделай нам market brief + контент-план первого месяца."
)
DEMO_TITLE = "Market & content brief (Wave-0 demo)"

AC8_P95_LATENCY_SECONDS = 120.0
AC10_MAX_COST_USD_PER_RUN = 0.30
AC9_BRIEF_MIN_WORDS = 1500
AC9_MATRIX_MIN_ROWS = 5
AC9_CONTENT_PLAN_POSTS = 10


@dataclass
class RunResult:
    run_index: int
    started_at: str
    completed_at: str | None = None
    duration_seconds: float = 0.0
    total_cost_credits: float = 0.0
    sse_events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    ac8_passed: bool = False
    ac9_passed: bool = False
    ac10_passed: bool = False


async def _execute_one_run(
    *,
    base_url: str,
    jwt: str,
    cell_id: str,
    run_index: int,
) -> RunResult:
    headers = {"Authorization": f"Bearer {jwt}"}
    result = RunResult(run_index=run_index, started_at=datetime.now(UTC).isoformat())
    start = perf_counter()
    async with httpx.AsyncClient(base_url=base_url, timeout=180.0) as client:
        try:
            create_resp = await client.post(
                f"/cells/{cell_id}/tasks",
                json={"title": DEMO_TITLE, "description": "", "prompt": DEMO_PROMPT},
                headers=headers,
            )
            create_resp.raise_for_status()
            task = create_resp.json()
            task_id = task["id"]
        except httpx.HTTPError as exc:
            result.errors.append(f"create_task: {exc}")
            return result

        try:
            async with client.stream(
                "GET",
                f"/cells/{cell_id}/tasks/{task_id}/stream",
                headers=headers,
                timeout=180.0,
            ) as stream:
                async for line in stream.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line.removeprefix("data: ")
                    try:
                        event = json.loads(payload)
                    except ValueError:
                        continue
                    result.sse_events.append(event)
                    # task.completed is the terminal event.
                    if event.get("event_type") == "task.completed":
                        result.total_cost_credits = float(
                            event.get("payload", {}).get("total_cost_credits", 0)
                        )
                        break
        except httpx.HTTPError as exc:
            result.errors.append(f"stream: {exc}")
            return result

        # Fetch final artifacts (brief, matrix, content-plan).
        try:
            artifacts_resp = await client.get(
                f"/cells/{cell_id}/tasks/{task_id}/artifacts", headers=headers
            )
            if artifacts_resp.status_code == 200:
                for art in artifacts_resp.json().get("items", []):
                    result.artifacts[art["artifact_type"]] = art.get("content_inline", {}).get(
                        "body", ""
                    )
        except httpx.HTTPError as exc:
            # Wave 0 artifact-list endpoint may not exist yet — fold into
            # brief as a fallback from the last SSE event.
            result.errors.append(f"artifacts: {exc} (non-fatal in Phase 00.5b)")

    elapsed = perf_counter() - start
    result.duration_seconds = elapsed
    result.completed_at = datetime.now(UTC).isoformat()

    # AC8 — p95 evaluated at cohort level, but per-run threshold is the cap.
    result.ac8_passed = elapsed <= AC8_P95_LATENCY_SECONDS
    # AC10 — cost ≤ 30¢. Assume 1 T-credit ≈ 1¢ for the Wave-0 ledger
    # (ADR-018 amendment fixes T-credit unit ≈ 0.01 USD).
    result.ac10_passed = result.total_cost_credits * 0.01 <= AC10_MAX_COST_USD_PER_RUN

    # AC9 — artifact shapes.
    brief_text = result.artifacts.get("brief", "")
    matrix_text = result.artifacts.get("competitive-matrix", "")
    plan_text = result.artifacts.get("content-plan", "")
    brief_words = len(brief_text.split())
    matrix_rows = (
        len(
            [
                line
                for line in matrix_text.splitlines()
                if line.startswith("|") and "---" not in line
            ]
        )
        - 1
    )  # subtract header
    plan_posts = len(re.findall(r"^\d+\.\s+\*\*", plan_text, flags=re.MULTILINE))
    result.ac9_passed = (
        brief_words >= AC9_BRIEF_MIN_WORDS
        and matrix_rows >= AC9_MATRIX_MIN_ROWS
        and plan_posts == AC9_CONTENT_PLAN_POSTS
    )
    return result


def _write_summary(output: Path, runs: list[RunResult]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for r in runs:
        (output / f"run_{r.run_index:03d}.json").write_text(
            json.dumps(asdict(r), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if not runs:
        return
    durations = [r.duration_seconds for r in runs]
    costs = [r.total_cost_credits for r in runs]
    p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 5 else max(durations)
    summary = {
        "runs": len(runs),
        "p95_latency_seconds": p95,
        "ac8_threshold_seconds": AC8_P95_LATENCY_SECONDS,
        "ac8_passed": p95 <= AC8_P95_LATENCY_SECONDS,
        "mean_cost_credits": statistics.mean(costs) if costs else 0.0,
        "max_cost_credits": max(costs) if costs else 0.0,
        "ac10_max_cost_usd": AC10_MAX_COST_USD_PER_RUN,
        "all_ac9_passed": all(r.ac9_passed for r in runs),
        "all_ac10_passed": all(r.ac10_passed for r in runs),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


async def _async_main(args: argparse.Namespace) -> int:
    output = Path(args.output)
    runs: list[RunResult] = []
    for i in range(1, args.runs + 1):
        print(f"[run {i}/{args.runs}] launching...")
        result = await _execute_one_run(
            base_url=args.api_base_url,
            jwt=args.jwt,
            cell_id=args.cell_id,
            run_index=i,
        )
        runs.append(result)
        print(
            f"[run {i}] elapsed={result.duration_seconds:.1f}s "
            f"cost={result.total_cost_credits} credits "
            f"ac8={result.ac8_passed} ac9={result.ac9_passed} ac10={result.ac10_passed}"
        )
        if result.errors:
            for err in result.errors:
                print(f"[run {i}] ERROR: {err}", file=sys.stderr)

    _write_summary(output, runs)

    if any(r.errors for r in runs):
        return 2
    if not all(r.ac8_passed and r.ac9_passed and r.ac10_passed for r in runs):
        return 1
    return 0


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo_market_brief",
        description=(
            "Run the productivity-core «Market & content brief» demo against "
            "a deployed API. Phase 00.6 runs this against staging for gate "
            "evidence (AC8 + AC9 + AC10)."
        ),
    )
    parser.add_argument(
        "--api-base-url",
        required=True,
        help="Base URL of the deployed API, e.g. http://localhost:8000/api/v1",
    )
    parser.add_argument("--jwt", required=True, help="Bearer JWT for an authenticated test user")
    parser.add_argument(
        "--cell-id",
        required=True,
        help="Cell UUID under which to run the demo (the user's productivity-core cell)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="How many independent runs to execute (Phase 00.6 uses 10 for p95)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./.tmp/demo/"),
        help="Directory for per-run JSON + summary.json",
    )
    return parser


def main() -> int:
    args = _build_argparser().parse_args()
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
