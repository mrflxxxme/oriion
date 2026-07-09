"""Assemble a founder-facing REVIEW-PACKAGE.md from the runner JSON + an assessment.

Keeps the LLM deliverables byte-exact (straight from the runner JSON); the
human quality assessment / verdict is supplied as a separate markdown file and
appended verbatim.

Run:
  python scripts/build_review_package.py --json /tmp/tg.json \
      --assessment /tmp/tg_assessment.md --title "..." --model "..." \
      --out .../REVIEW-PACKAGE.md
"""

from __future__ import annotations

import argparse
import json
from datetime import date


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--assessment", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as fh:
        d = json.load(fh)
    with open(args.assessment, encoding="utf-8") as fh:
        assessment = fh.read()

    adv_pass = sum(1 for a in d["adversarial"] if a["ok"])
    adv_total = len(d["adversarial"])
    lines: list[str] = []
    lines.append(f"# {args.title}")
    lines.append("")
    lines.append(
        "> Live vertical review package — real deliverables from the in-process "
        "Master plan+synthesis path against live DeepSeek (no DB/Docker/API; the "
        "pure LLM-contract path). Generated for the founder's `draft → reviewed` "
        "sign-off decision."
    )
    lines.append("")
    lines.append("## Run metadata")
    lines.append("")
    lines.append(f"- **Vertical:** `{d['vertical']}`")
    lines.append(f"- **Date:** {date.today().isoformat()}")
    lines.append(
        f"- **Models:** plan `{d['provider_model_plan']}` (structured `MasterPlan`) · "
        f"synthesis `{d['provider_model_synth']}` (markdown deliverable)"
    )
    lines.append(
        f"- **Tokens:** in={d['tokens_in']:,} out={d['tokens_out']:,} · "
        f"**est. cost ≈ ${d['cost_usd']:.4f}**"
    )
    lines.append(f"- **Adversarial (safety) probes:** {adv_pass}/{adv_total} pass")
    lines.append(
        f"- **Tasks exercised:** {len(d['tasks'])} "
        "(plan + full synthesis deliverable each)"
    )
    lines.append("")
    lines.append(
        "Reproduce: `uv run --directory backend python "
        f"scripts/review_artifacts_runner.py --vertical {d['vertical']} --out out.json`"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Assessment first, so the founder reads the verdict before the raw material.
    lines.append(assessment.rstrip())
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Adversarial (safety) probe results")
    lines.append("")
    lines.append(f"**{adv_pass}/{adv_total} pass** (100% required for the Level-B gate).")
    lines.append("")
    lines.append("| Probe | Result | Heuristic check |")
    lines.append("|-------|--------|-----------------|")
    for a in d["adversarial"]:
        res = "✅ PASS" if a["ok"] else "❌ FAIL"
        note = a["note"].replace("|", "\\|")
        lines.append(f"| {a['slug']} | {res} | {note} |")
    lines.append("")
    lines.append("<details><summary>probe trigger prompts</summary>")
    lines.append("")
    for a in d["adversarial"]:
        lines.append(f"- **{a['slug']}**: {a['trigger']}")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Task deliverables (full)")
    lines.append("")
    lines.append(
        "For each task: the **user prompt**, the **plan** the model produced "
        "(objective + domain constraints + success criteria), and the **full "
        "synthesis deliverable** — exactly as the vertical generated it."
    )
    lines.append("")

    for t in d["tasks"]:
        lines.append(f"### {t['task_id']} — {t['title']}")
        lines.append("")
        lines.append(f"*Source: {t['source']}*")
        lines.append("")
        lines.append("**User prompt:**")
        lines.append("")
        lines.append("> " + t["user_prompt"].replace("\n", "\n> "))
        lines.append("")
        p = t["plan"]
        lines.append("**Plan — objective:**")
        lines.append("")
        lines.append(p["objective"])
        lines.append("")
        lines.append("**Plan — domain constraints:**")
        lines.append("")
        for c in p["domain_constraints"]:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("**Plan — success criteria:**")
        lines.append("")
        for c in p["success_criteria"]:
            lines.append(f"- {c}")
        lines.append("")
        lines.append(
            f"**Synthesis deliverable** (tokens in={t['tokens']['in']:,} "
            f"out={t['tokens']['out']:,}):"
        )
        lines.append("")
        lines.append("<details><summary>expand full deliverable</summary>")
        lines.append("")
        lines.append(t["synthesis_markdown"])
        lines.append("")
        lines.append("</details>")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {args.out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
