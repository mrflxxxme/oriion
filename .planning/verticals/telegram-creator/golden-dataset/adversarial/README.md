# `verticals/telegram-creator/golden-dataset/adversarial/` — Adversarial probes

> Adversarial test cases that probe failure modes in the Telegram-creator
> vertical Master-Agent: hallucinated monetization figures, missing
> RU-regulatory compliance (ad-marking, РКН blogger-registry), autonomous
> send-side requests, and PII leaks. Mirrors
> [`verticals/agency-marketing-ru/golden-dataset/adversarial/`](../../agency-marketing-ru/golden-dataset/adversarial/)
> in shape (frontmatter + `## Probe trigger` + `## Expected behavior` +
> `## Forbidden behaviors` + `## Pass criteria`).

## Files

5 probe files (A001-A005), each self-contained (no shared state between
them).

## Pass rate target

**100%** per [ADR-026](../../../decisions/ADR-026-vertical-expertise-pipeline.md)
§3. A single adversarial failure blocks the vertical preset's
`draft → reviewed` promotion.

## Adding new probes

When the Telegram-creator team encounters a new failure mode in
production/staging/red-team session, add the minimal reproducer here as a
new `A00N-<slug>.md` probe.

## Evaluator integration

The `evaluator` AI role (per [ADR-023](../../../decisions/ADR-023-ai-team-runtime.md))
runs all adversarial probes against any candidate prompt change to the
Telegram-creator team. The 100% pass rate is a hard gate. Not run this
phase — see `../README.md` "Status & next steps."
