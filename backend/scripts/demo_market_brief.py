"""Runnable demo: «Market & content brief» end-to-end against any deployed API.

Phase 00.5b Commit 7 SHIP, Phase 00.6 RUNS:
    * Ships in this PR but does NOT execute in CI (no live LLM keys).
    * Phase 00.6 PR-B staging deploy runs this with --runs 10 to collect
      gate evidence for AC8 (cohort p95 ≤ 120s) + AC9 (per-run artifact
      shape) + AC10 (per-run cost ≤ 30¢) — D5 of gates/wave-0-to-1.md.

Flow per run (Phase 00.6 PR-B — uses the new inline-dispatch endpoint):
    1. POST /cells/{cell_id}/tasks            → create a queued task.
    2. POST /cells/{cell_id}/tasks/{id}/run   → synchronously runs the
       orchestrator (Wave-0 deterministic researcher→analyst→writer
       pipeline). Blocks until the orchestration finishes and returns the
       structured CoordinatorOutput (summary + artifacts + total cost).
    3. GET  /cells/{cell_id}/tasks/{id}/stream → drain-replay of the SSE
       event ledger (the orchestration already completed, so the stream
       returns the full task.started→…→task.completed log immediately).
       Captured purely as audit evidence.

Wall-clock is measured around step 2 (the real orchestration latency).

AC semantics (aligned with phase-spec § «AC tolerance clarification»):
    * AC8  — **cohort** p95 latency ≤ 120s (NOT a per-run cap). Evaluated
             across all runs in summary.json.
    * AC9  — per-run artifact shape: brief ≥1500 RU words, matrix ≥5×4,
             content-plan == 10 posts.
    * AC10 — per-run cost cap: total_cost_credits × 0.01 ≤ 0.30 USD.

Usage::

    python -m scripts.demo_market_brief \\
        --api-base-url https://staging.oriion.dev/api/v1 \\
        --jwt $env:DEMO_JWT \\
        --cell-id $env:DEMO_CELL_ID \\
        --runs 10 \\
        --output .planning/gates/evidence/wave-0-to-1/

Exit codes:
    0 — cohort p95 ≤ 120s AND (failures ≤ --tolerate-failures) for AC9+AC10
    1 — cohort p95 > 120s OR per-run AC9/AC10 failures exceed tolerance
    2 — transport / auth error (treat as infra failure, not an AC verdict)

The strict default (--tolerate-failures 0) enforces the phase-spec «all
10/10» invariant. The founder may pass --tolerate-failures 1 to honour the
gate D5 «≥9/10» acceptance latitude (α decision-7).
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
TCREDIT_USD = 0.01  # ADR-018: 1 T-credit ≈ 0.01 USD
AC9_BRIEF_MIN_WORDS = 1500
AC9_MATRIX_MIN_ROWS = 5
AC9_MATRIX_MIN_COLS = 4
AC9_CONTENT_PLAN_POSTS = 10

# Artifact-type keys emitted by the Wave-0 ScriptedCoordinator
# (src/runtime/dispatch.py::_ARTIFACT_KIND). The writer's "brief" artifact
# carries BOTH the market brief and the 10-post content plan.
ARTIFACT_MATRIX = "matrix"
ARTIFACT_BRIEF = "brief"


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
    warnings: list[str] = field(default_factory=list)
    # AC8 is a COHORT metric — see summary.json, not a per-run flag.
    ac9_passed: bool = False
    ac10_passed: bool = False
    brief_words: int = 0
    matrix_rows: int = 0
    matrix_cols: int = 0
    content_plan_posts: int = 0

    @property
    def transport_ok(self) -> bool:
        # `warnings` (e.g. evidence-only SSE-replay hiccups) do NOT gate the
        # AC verdict; only hard `errors` (create/run transport) do.
        return not self.errors


def _count_matrix_rows(matrix_text: str) -> int:
    """Count data rows in a markdown table (excludes header + separator)."""
    body_rows = [
        line
        for line in matrix_text.splitlines()
        if line.strip().startswith("|") and "---" not in line
    ]
    return max(len(body_rows) - 1, 0)  # subtract header row


def _matrix_max_cols(matrix_text: str) -> int:
    """Max |-delimited cell count across data rows (AC9 requires >=4 columns)."""
    best = 0
    for line in matrix_text.splitlines():
        s = line.strip()
        if s.startswith("|") and "---" not in s:
            cells = s.strip("|").split("|")
            best = max(best, len(cells))
    return best


def _count_content_plan_posts(text: str) -> int:
    """Count content-plan posts across the writer's content-plan idioms.

    F-CR-1 / F-TR-1 audit fix: the production writer role-prompt
    (contracts/role-prompts/writer.md §6 few-shot) emits each post as an H3
    header `### Пост N — <channel> — <day>`. An earlier draft used a
    numbered-bold list `N. **...**`. Match BOTH so AC9 scores REAL staging
    output, not just the synthetic test fixture. The dispatch writer
    sub-prompt (runtime/dispatch.py) also pins the H3 idiom belt-and-suspenders.
    """
    pattern = r"(?:^###\s+Пост\s+\d+)|(?:^\s*\d+\.\s+\*\*)"
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def _evaluate_ac9(result: RunResult) -> None:
    """Populate AC9 per-run artifact-shape metrics + pass flag."""
    brief_text = result.artifacts.get(ARTIFACT_BRIEF, "")
    matrix_text = result.artifacts.get(ARTIFACT_MATRIX, "")

    result.brief_words = len(brief_text.split())
    result.matrix_rows = _count_matrix_rows(matrix_text)
    result.matrix_cols = _matrix_max_cols(matrix_text)
    # The content plan lives inside the writer's "brief" artifact.
    result.content_plan_posts = _count_content_plan_posts(brief_text)

    result.ac9_passed = (
        result.brief_words >= AC9_BRIEF_MIN_WORDS
        and result.matrix_rows >= AC9_MATRIX_MIN_ROWS
        and result.matrix_cols >= AC9_MATRIX_MIN_COLS
        and result.content_plan_posts == AC9_CONTENT_PLAN_POSTS
    )


def _ingest_run_output(result: RunResult, run_payload: dict[str, Any]) -> None:
    """Fold the POST /run response (CoordinatorOutput) into the RunResult."""
    output = run_payload.get("result", {}) or {}
    result.total_cost_credits = float(output.get("total_cost_credits", 0) or 0)
    for art in output.get("artifacts", []):
        art_type = art.get("type", "")
        result.artifacts[art_type] = art.get("path_or_inline", "")


async def _execute_one_run(
    *,
    base_url: str,
    jwt: str,
    cell_id: str,
    run_index: int,
) -> RunResult:
    headers = {"Authorization": f"Bearer {jwt}"}
    result = RunResult(run_index=run_index, started_at=datetime.now(UTC).isoformat())

    async with httpx.AsyncClient(base_url=base_url, timeout=180.0) as client:
        # 1) Create the queued task.
        try:
            create_resp = await client.post(
                f"/cells/{cell_id}/tasks",
                json={"title": DEMO_TITLE, "description": "", "prompt": DEMO_PROMPT},
                headers=headers,
            )
            create_resp.raise_for_status()
            task_id = create_resp.json()["id"]
        except httpx.HTTPError as exc:
            result.errors.append(f"create_task: {exc}")
            return result

        # 2) Dispatch synchronously (this is the orchestration — measure here).
        start = perf_counter()
        try:
            run_resp = await client.post(
                f"/cells/{cell_id}/tasks/{task_id}/run",
                headers=headers,
                timeout=180.0,
            )
            run_resp.raise_for_status()
            _ingest_run_output(result, run_resp.json())
        except httpx.HTTPError as exc:
            result.errors.append(f"run_task: {exc}")
            return result
        result.duration_seconds = perf_counter() - start

        # 3) Drain-replay the SSE ledger as audit evidence (already complete).
        try:
            async with client.stream(
                "GET",
                f"/cells/{cell_id}/tasks/{task_id}/stream",
                headers=headers,
                timeout=30.0,
            ) as stream:
                async for line in stream.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        result.sse_events.append(json.loads(line.removeprefix("data: ")))
                    except ValueError:
                        continue
        except httpx.HTTPError as exc:
            # Non-fatal: the run already produced the result; the SSE replay
            # is evidence-only — record as a warning, NOT a gating error.
            result.warnings.append(f"stream: {exc}")

    result.completed_at = datetime.now(UTC).isoformat()

    # AC10 — per-run cost cap.
    result.ac10_passed = result.total_cost_credits * TCREDIT_USD <= AC10_MAX_COST_USD_PER_RUN
    # AC9 — per-run artifact shape.
    _evaluate_ac9(result)
    return result


def _cohort_p95(durations: list[float]) -> float:
    if not durations:
        return 0.0
    if len(durations) >= 5:
        return statistics.quantiles(durations, n=20)[18]
    return max(durations)


def _build_summary(runs: list[RunResult]) -> dict[str, Any]:
    durations = [r.duration_seconds for r in runs if r.transport_ok]
    costs = [r.total_cost_credits for r in runs if r.transport_ok]
    p95 = _cohort_p95(durations)
    runs_passed = sum(1 for r in runs if r.transport_ok and r.ac9_passed and r.ac10_passed)
    return {
        "runs": len(runs),
        "runs_with_transport_ok": len(durations),
        # AC8 — cohort metric.
        "ac8_cohort_p95_seconds": p95,
        "ac8_threshold_seconds": AC8_P95_LATENCY_SECONDS,
        "ac8_passed": p95 <= AC8_P95_LATENCY_SECONDS if durations else False,
        # AC9 / AC10 — per-run, aggregated.
        "ac9_per_run_all_pass": all(r.ac9_passed for r in runs if r.transport_ok)
        and bool(durations),
        "ac10_per_run_all_pass": all(r.ac10_passed for r in runs if r.transport_ok)
        and bool(durations),
        "runs_passed": runs_passed,
        "mean_cost_credits": statistics.mean(costs) if costs else 0.0,
        "max_cost_credits": max(costs) if costs else 0.0,
        "ac10_max_cost_usd": AC10_MAX_COST_USD_PER_RUN,
    }


def _write_summary(output: Path, runs: list[RunResult]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    for r in runs:
        (output / f"run_{r.run_index:03d}.json").write_text(
            json.dumps(asdict(r), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    summary = _build_summary(runs)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _decide_exit_code(
    runs: list[RunResult], summary: dict[str, Any], *, tolerate_failures: int
) -> int:
    """Exit-code policy (cohort AC8 + per-run AC9/AC10 with tolerance).

    2 — any transport/infra error (not an AC verdict).
    1 — cohort p95 > 120s OR (AC9-or-AC10 per-run failures > tolerance).
    0 — otherwise.
    """
    if any(r.errors for r in runs):
        return 2
    if not summary["ac8_passed"]:
        return 1
    per_run_failures = sum(1 for r in runs if not (r.ac9_passed and r.ac10_passed))
    if per_run_failures > tolerate_failures:
        return 1
    return 0


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
            f"ac9={result.ac9_passed} (brief={result.brief_words}w "
            f"matrix={result.matrix_rows}r×{result.matrix_cols}c "
            f"plan={result.content_plan_posts}p) "
            f"ac10={result.ac10_passed}"
        )
        for err in result.errors:
            print(f"[run {i}] ERROR: {err}", file=sys.stderr)

    summary = _write_summary(output, runs)
    return _decide_exit_code(runs, summary, tolerate_failures=args.tolerate_failures)


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo_market_brief",
        description=(
            "Run the productivity-core «Market & content brief» demo against "
            "a deployed API. Phase 00.6 PR-B runs this against staging for gate "
            "evidence (AC8 cohort p95 + AC9 + AC10 per-run)."
        ),
    )
    parser.add_argument(
        "--api-base-url",
        required=True,
        help="Base URL of the deployed API, e.g. https://staging.oriion.dev/api/v1",
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
        help="How many independent runs to execute (Phase 00.6 uses 10 for cohort p95)",
    )
    parser.add_argument(
        "--tolerate-failures",
        type=int,
        default=0,
        help=(
            "Max per-run AC9/AC10 failures to still exit 0 (default 0 = strict "
            "10/10; pass 1 for the gate D5 «≥9/10» founder latitude)"
        ),
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
