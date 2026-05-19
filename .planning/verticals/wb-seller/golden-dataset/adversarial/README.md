# `verticals/wb-seller/golden-dataset/adversarial/` — Adversarial probes

> Adversarial test cases that probe failure modes in the WB-Seller vertical
> team: jailbreak attempts, ambiguous inputs, contradictory user goals,
> prompt-injection vectors, and OOD (out-of-domain) requests.

## Files

5 probe files covering distinct failure-mode categories. Each probe is a YAML test case with `input`, `expected_refusal`, and `unacceptable_outputs` fields.

## Pass rate target

**100 %** per [ADR-026](../../../../decisions/ADR-026-vertical-expertise-pipeline.md) §5. A single adversarial failure blocks the vertical preset's Wave-acceptance gate (see `gates/wave-2-to-3.md` when authored).

## Adding new probes

When the WB-Seller team encounters a new failure mode in production / staging / red-team session, add the minimal reproducer here as a YAML probe. Probes should be self-contained — no shared state between them.

## Evaluator integration

The `evaluator` AI role (per [ADR-023](../../../../decisions/ADR-023-ai-team-runtime.md)) runs all adversarial probes against any candidate prompt change to the WB-Seller team. The 100 % pass rate is a hard gate.
