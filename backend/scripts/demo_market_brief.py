"""Runnable demo: «Market & content brief» end-to-end against any deployed API.

Phase 00.5b Commit 7 SHIP, Phase 00.6 RUNS:
    * Ships in this PR but does NOT execute in CI (no live LLM keys).
    * Phase 00.6 PR-B staging deploy runs this with --runs 10 to collect
      gate evidence for AC8 (cohort p95 ≤ 120s) + AC9 (per-run artifact
      shape) + AC10 (per-run cost ≤ 30¢) — D5 of gates/wave-0-to-1.md.

Flow per run (Phase 01.1 infra-PR — async Dramatiq dispatch, ADR-034):
    1. POST /cells/{cell_id}/tasks            → create a queued task.
    2. POST /cells/{cell_id}/tasks/{id}/run   → enqueues the dispatch actor and
       returns 202 in <1s (NO result in the body). Measured = dispatch latency.
    3. GET  /cells/{cell_id}/tasks/{id}/stream → subscribe to the SSE ledger;
       wait for task.completed, which carries the CoordinatorOutput (summary +
       artifacts + total cost). Measured = generation wall-clock (SLI).

AC semantics (reframed per ADR-034):
    * AC8  — **HARD gate**: cohort p95 DISPATCH latency ≤ 1s (the async endpoint
             returns 202 fast). Generation wall-clock (dispatch → task.completed)
             is a reported SLI, NOT a gate — perceived latency is decoupled from
             generation length by the worker + live SSE progress.
    * AC9  — per-run artifact shape: brief ≥1500 RU words, matrix ≥5×4,
             content-plan == 10 posts (read from the task.completed payload).
    * AC10 — per-run cost cap: total_cost_credits × 0.01 ≤ 0.30 USD.

Usage::

    python -m scripts.demo_market_brief \\
        --api-base-url https://staging.oriion.dev/api/v1 \\
        --jwt $env:DEMO_JWT \\
        --cell-id $env:DEMO_CELL_ID \\
        --runs 10 \\
        --output .planning/gates/evidence/wave-0-to-1/

Exit codes:
    0 — dispatch p95 ≤ 1s AND (failures ≤ --tolerate-failures) for AC9+AC10
    1 — dispatch p95 > 1s OR per-run AC9/AC10 failures exceed tolerance
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
    "Запускаем платформу AI-команд для SMB в РФ. Подготовь маркетинговый пакет: "
    "(1) market brief на русском ≥1500 слов (контекст рынка, ICP, конкуренты, "
    "позиционирование, риски, next steps); "
    "(2) конкурентную матрицу ≥5 строк × ≥4 колонки с заголовком "
    "«| Игрок | Сегмент | Сильная сторона | Слабая сторона |»; "
    "(3) контент-план ровно на 10 постов (Telegram + vc.ru), каждый пост — "
    "заголовком «### Пост N — <канал> — <день>»."
)
DEMO_TITLE = "Market & content brief (Wave-0 demo)"

# AC8 reframed (ADR-034): async dispatch returns 202 in <1s, so the HARD gate is
# now dispatch latency. Total generation wall-clock (dispatch → task.completed) is
# kept as a reported SLI, NOT a gate — perceived latency is decoupled from
# generation length by the async worker + live SSE progress.
AC8_DISPATCH_P95_SECONDS = 1.0
AC8_GENERATION_SLI_SECONDS = 120.0  # informational reference only (was the old gate)
AC10_MAX_COST_USD_PER_RUN = 0.30
TCREDIT_USD = 0.01  # ADR-018: 1 T-credit ≈ 0.01 USD
AC9_BRIEF_MIN_WORDS = 1500
AC9_MATRIX_MIN_ROWS = 5
AC9_MATRIX_MIN_COLS = 4
AC9_CONTENT_PLAN_POSTS = 10

# Artifact-type keys the Coordinator names in its plan (AC-W1-24: artifact_type
# travels in the delegation_plan, no longer a code-side map). The writer's "brief"
# artifact carries BOTH the market brief and the 10-post content plan.
ARTIFACT_MATRIX = "matrix"
ARTIFACT_BRIEF = "brief"


@dataclass
class RunResult:
    run_index: int
    started_at: str
    completed_at: str | None = None
    # AC8 reframed: dispatch_seconds is the hard-gate metric (POST /run → 202);
    # generation_seconds (dispatch → task.completed via SSE) is a tracked SLI.
    dispatch_seconds: float = 0.0
    generation_seconds: float = 0.0
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
    # Match a post heading at ANY markdown level, tolerating the real-LLM
    # quirk where the model wraps its own heading around the instructed format
    # (e.g. `#### ### Пост 1 — Telegram — Пн`). `^#{1,6}[#\s]*Пост\s+\d+`
    # covers `### Пост 1`, `## Пост 1`, `#### ### Пост 1`; the second branch
    # keeps the numbered-bold fallback.
    # The H3 post-header and the numbered-bold list are MUTUALLY EXCLUSIVE
    # idioms, not additive. When H3 headers are present (the production writer's
    # contracted format), count ONLY those — counting both over-counts when the
    # market-brief prose in the SAME artifact contains numbered-bold lists
    # (e.g. "1. **Контекст рынка**"). That false-positive failed AC9 on real
    # output that actually had exactly 10 posts (Phase 01.1 live validation:
    # 10 `### Пост` headers + 15 numbered-bold prose lines → spurious 25).
    h3_posts = re.findall(r"^#{1,6}[#\s]*Пост\s+\d+", text, flags=re.MULTILINE)
    if h3_posts:
        return len(h3_posts)
    return len(re.findall(r"^\s*\d+\.\s+\*\*", text, flags=re.MULTILINE))


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

        # 2) Enqueue async dispatch — measure DISPATCH latency (AC8 hard gate).
        #    Returns 202 in <1s (ADR-034); the orchestration runs in the worker
        #    and the result arrives via the SSE task.completed frame, not this body.
        dispatch_start = perf_counter()
        try:
            run_resp = await client.post(
                f"/cells/{cell_id}/tasks/{task_id}/run",
                headers=headers,
                timeout=30.0,
            )
            run_resp.raise_for_status()
        except httpx.HTTPError as exc:
            result.errors.append(f"run_task: {exc}")
            return result
        result.dispatch_seconds = perf_counter() - dispatch_start

        # 3) Subscribe to the SSE ledger: measure GENERATION wall-clock (dispatch →
        #    task.completed) as a tracked SLI, and pull the CoordinatorOutput from
        #    the task.completed frame (the result left the POST /run body — ADR-034).
        completed = False
        try:
            async with client.stream(
                "GET",
                f"/cells/{cell_id}/tasks/{task_id}/stream",
                headers=headers,
                timeout=300.0,
            ) as stream:
                current_event: str | None = None
                async for line in stream.aiter_lines():
                    if line.startswith("event: "):
                        current_event = line.removeprefix("event: ").strip()
                        continue
                    if not line.startswith("data: "):
                        continue
                    try:
                        payload = json.loads(line.removeprefix("data: "))
                    except ValueError:
                        continue
                    result.sse_events.append(payload)
                    if current_event in {"task.completed", "task.failed", "task.cancelled"}:
                        result.generation_seconds = perf_counter() - dispatch_start
                        if current_event == "task.completed":
                            _ingest_run_output(result, payload)
                            completed = True
                        else:
                            result.errors.append(f"task terminal event: {current_event}")
                        break
        except httpx.HTTPError as exc:
            result.errors.append(f"stream: {exc}")
            return result
        if not completed and not result.errors:
            result.errors.append("stream ended before task.completed")

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
    dispatch_durations = [r.dispatch_seconds for r in runs if r.transport_ok]
    generation_durations = [r.generation_seconds for r in runs if r.transport_ok]
    costs = [r.total_cost_credits for r in runs if r.transport_ok]
    dispatch_p95 = _cohort_p95(dispatch_durations)
    generation_p95 = _cohort_p95(generation_durations)
    runs_passed = sum(1 for r in runs if r.transport_ok and r.ac9_passed and r.ac10_passed)
    return {
        "runs": len(runs),
        "runs_with_transport_ok": len(dispatch_durations),
        # AC8 (reframed, ADR-034) — HARD gate is dispatch latency (202 <1s).
        "ac8_dispatch_p95_seconds": dispatch_p95,
        "ac8_dispatch_threshold_seconds": AC8_DISPATCH_P95_SECONDS,
        "ac8_passed": dispatch_p95 <= AC8_DISPATCH_P95_SECONDS if dispatch_durations else False,
        # Generation wall-clock (dispatch → task.completed) — tracked SLI, NOT a
        # gate; perceived latency is decoupled via async + live SSE progress.
        "generation_p95_seconds": generation_p95,
        "generation_sli_reference_seconds": AC8_GENERATION_SLI_SECONDS,
        # AC9 / AC10 — per-run, aggregated.
        "ac9_per_run_all_pass": all(r.ac9_passed for r in runs if r.transport_ok)
        and bool(dispatch_durations),
        "ac10_per_run_all_pass": all(r.ac10_passed for r in runs if r.transport_ok)
        and bool(dispatch_durations),
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
    """Exit-code policy (reframed AC8 dispatch gate + per-run AC9/AC10 tolerance).

    2 — any transport/infra error (not an AC verdict).
    1 — dispatch p95 > AC8_DISPATCH_P95_SECONDS OR (AC9-or-AC10 per-run failures >
        tolerance). Generation wall-clock is an SLI and never gates (ADR-034).
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
            f"[run {i}] dispatch={result.dispatch_seconds:.2f}s "
            f"generation={result.generation_seconds:.1f}s "
            f"cost={result.total_cost_credits} credits "
            f"ac9={result.ac9_passed} (brief={result.brief_words}w "
            f"matrix={result.matrix_rows}rx{result.matrix_cols}c "
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


def _force_utf8_console() -> None:
    """Windows consoles default to cp1251 — force UTF-8 so RU content + symbols
    in progress/error lines don't crash the run with UnicodeEncodeError (the
    JSON evidence is already utf-8). errors='replace' keeps it crash-proof."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _force_utf8_console()
    args = _build_argparser().parse_args()
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
