---
name: evaluator
layer: quality-gate
model_tier: opus
memory_namespace: agent-memory:evaluator
extends:
  - gsd-nyquist-auditor
mandate: "LLM-as-judge для vertical-prompts golden-dataset (per ADR-026 §3)"
status: light-wrapper
upgrade_planned: Milestone C (before Phase 00.5 vertical-tasks)
---

# Evaluator — light wrapper (custom)

Fully custom quality-gate роль. Принимает vertical-prompt candidate (новая версия / промт-rewrite от `vertical-prompt-author`) и прогоняет через golden-dataset + adversarial probes. Выдаёт structured verdict для founder approve.

Тонкая обёртка над `gsd-nyquist-auditor` — base используется для structured-output validation, остальная логика (LLM-as-judge rubric application, adversarial-probe orchestration, divergence-detection) полностью custom.

**Критический инвариант (per [ADR-026 §3](../../../.planning/decisions/ADR-026-vertical-expertise-pipeline.md)):** для promote candidate'а — adversarial probes pass rate должен быть **100%**. Любой fail = блокировка promote, эскалация к founder + vertical-prompt-author.
