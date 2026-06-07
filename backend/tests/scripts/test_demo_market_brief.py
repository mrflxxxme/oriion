"""Unit tests for scripts/demo_market_brief.py — AC8 cohort-semantic + exit code.

Phase 00.6 PR-B Commit 2. Tests the pure-logic seams (AC parsing, cohort p95,
exit-code policy) without any network — the live 10× run against staging is the
gate evidence (D5), this just proves the measurement logic is correct.
"""

from __future__ import annotations

from scripts.demo_market_brief import (
    AC8_P95_LATENCY_SECONDS,
    RunResult,
    _build_summary,
    _count_content_plan_posts,
    _count_matrix_rows,
    _decide_exit_code,
    _evaluate_ac9,
    _ingest_run_output,
)


def _passing_run(idx: int, *, duration: float = 50.0) -> RunResult:
    r = RunResult(run_index=idx, started_at="t")
    r.duration_seconds = duration
    r.total_cost_credits = 5.0  # 5 credits × 0.01 = 0.05 USD ≤ 0.30
    r.artifacts = {
        "brief": ("слово " * 1600) + _content_plan_block(),
        "matrix": _matrix_block(6),
    }
    _evaluate_ac9(r)
    r.ac10_passed = r.total_cost_credits * 0.01 <= 0.30
    return r


def _matrix_block(rows: int) -> str:
    header = "| Игрок | Сегмент | Сильная сторона | Слабая сторона |"
    sep = "| --- | --- | --- | --- |"
    body = "\n".join(f"| p{i} | s | a | b |" for i in range(rows))
    return f"{header}\n{sep}\n{body}"


def _content_plan_block() -> str:
    return "\n" + "\n".join(f"{i}. **Пост {i}** описание" for i in range(1, 11))


# ── parsing helpers ───────────────────────────────────────────────────────


def test_count_matrix_rows_excludes_header_and_separator() -> None:
    assert _count_matrix_rows(_matrix_block(6)) == 6
    assert _count_matrix_rows("") == 0


def test_count_content_plan_posts() -> None:
    assert _count_content_plan_posts(_content_plan_block()) == 10
    assert _count_content_plan_posts("no posts here") == 0


def test_ingest_run_output_maps_artifacts_and_cost() -> None:
    r = RunResult(run_index=1, started_at="t")
    _ingest_run_output(
        r,
        {
            "result": {
                "total_cost_credits": "7.5",
                "artifacts": [
                    {"id": "a", "type": "matrix", "path_or_inline": "M"},
                    {"id": "b", "type": "brief", "path_or_inline": "B"},
                ],
            }
        },
    )
    assert r.total_cost_credits == 7.5
    assert r.artifacts == {"matrix": "M", "brief": "B"}


def test_evaluate_ac9_pass_and_fail() -> None:
    good = _passing_run(1)
    assert good.ac9_passed is True
    assert good.brief_words >= 1500
    assert good.matrix_rows == 6
    assert good.content_plan_posts == 10

    short = RunResult(run_index=2, started_at="t")
    short.artifacts = {"brief": "too short", "matrix": _matrix_block(6)}
    _evaluate_ac9(short)
    assert short.ac9_passed is False


# ── cohort p95 + summary ──────────────────────────────────────────────────


def test_build_summary_cohort_p95_and_aggregates() -> None:
    runs = [_passing_run(i, duration=float(40 + i)) for i in range(1, 11)]
    summary = _build_summary(runs)
    assert summary["runs"] == 10
    assert summary["ac8_cohort_p95_seconds"] <= AC8_P95_LATENCY_SECONDS
    assert summary["ac8_passed"] is True
    assert summary["ac9_per_run_all_pass"] is True
    assert summary["ac10_per_run_all_pass"] is True
    assert summary["runs_passed"] == 10


def test_build_summary_flags_slow_cohort() -> None:
    runs = [_passing_run(i, duration=200.0) for i in range(1, 11)]
    summary = _build_summary(runs)
    assert summary["ac8_cohort_p95_seconds"] > AC8_P95_LATENCY_SECONDS
    assert summary["ac8_passed"] is False


# ── exit code policy ──────────────────────────────────────────────────────


def test_exit_code_all_pass_is_zero() -> None:
    runs = [_passing_run(i) for i in range(1, 11)]
    summary = _build_summary(runs)
    assert _decide_exit_code(runs, summary, tolerate_failures=0) == 0


def test_exit_code_transport_error_is_two() -> None:
    runs = [_passing_run(i) for i in range(1, 10)]
    bad = RunResult(run_index=10, started_at="t")
    bad.errors.append("run_task: boom")
    runs.append(bad)
    summary = _build_summary(runs)
    assert _decide_exit_code(runs, summary, tolerate_failures=5) == 2


def test_exit_code_slow_cohort_is_one() -> None:
    runs = [_passing_run(i, duration=200.0) for i in range(1, 11)]
    summary = _build_summary(runs)
    assert _decide_exit_code(runs, summary, tolerate_failures=0) == 1


def test_exit_code_one_ac_failure_strict_is_one_tolerant_is_zero() -> None:
    runs = [_passing_run(i) for i in range(1, 10)]
    failing = _passing_run(10)
    failing.ac9_passed = False  # one bad artifact-shape run
    runs.append(failing)
    summary = _build_summary(runs)
    # strict (0 tolerance) → 1
    assert _decide_exit_code(runs, summary, tolerate_failures=0) == 1
    # founder latitude (≥9/10 → tolerate 1) → 0
    assert _decide_exit_code(runs, summary, tolerate_failures=1) == 0


def test_warnings_do_not_gate_transport_ok() -> None:
    r = _passing_run(1)
    r.warnings.append("stream: hiccup")
    assert r.transport_ok is True
