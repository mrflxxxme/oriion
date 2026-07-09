---
title: "Telegram-крейтор Vertical — Changelog"
vertical_slug: telegram_creator
last-updated: 2026-07-09
---

# Telegram-крейтор Vertical — Changelog

## 0.1.0 — 2026-07-09 — Initial materialization (Phase 01.10, autonomous runner)

### Added

- `domain-brief.md` — cited AI-baseline research (ADR-026 §7 research-first
  step): ICP/JTBD, content formats + cadence, monetization channels (sponsored
  posts, Telegram Ad Platform revenue-share, Telegram Stars), RU regulatory
  specifics (ФЗ-38 ad-marking, РКН reestr-blogerov 10K+ trigger), engagement
  measurement (ERR + size-relative benchmarks).
- `README.md` — ICP / JTBD / KPI overview, agent team table, connector-tool
  scope note.
- `domain-glossary.md` — Telegram-creator-specific terminology (рубрика,
  ERR, Telegram Stars, РКН-реестр блогеров, erid, etc.).
- `workflow-dag.md` — Master → Coordinator → {Researcher, Analyst,
  Community-manager} → Writer → Community-manager → Coordinator → Master DAG
  for the 5 primary tasks.
- `kpis.md` — Wave-by-Wave business metrics aligned with ADR-025 gates +
  domain-specific quality signals (ad-marking compliance rate, РКН-trigger
  accuracy, no-fabricated-monetization-estimate).
- `REVIEW-CHECKLIST.md` — founder + evaluator review gates (P-INIT-4),
  Telegram-creator-specific compliance checks.
- `prompts/README.md` — prompt inventory + canonical-location map (Master
  prompt lives under `contracts/role-prompts/masters/`, per the ADR-029
  convention established by `agency-marketing-ru`).
- `prompts/community_manager.md` — vertical-specific specialist prompt
  (draft, v0.1.0) — the only archetype carrying the Telegram-bot connector
  `tools_allowed`.
- `contracts/role-prompts/masters/telegram_creator.md` — the Master-Agent
  prompt (draft, v0.1.0), 9-section contract per `role_prompt_loader.py`,
  grounded in `domain-brief.md`.
- `golden-dataset/README.md` — methodology (mirrors `agency-marketing-ru`'s
  Master-Agent-aware rubric: strategic framing / domain expertise /
  measurability / RF-realism & compliance / synthesis quality).
- `golden-dataset/tasks/001-030` — **30 golden tasks** (AI-baseline), 5
  primary-task buckets × 6 variants (2 easy / 3 medium / 1 hard): content-plan,
  post-drafting, channel-audit, compliance-audit, monetization-and-repurposing.
- `golden-dataset/adversarial/A001-A005` — 5 adversarial probes: fabricated
  monetization estimate, missing ad-marking, missing РКН-registry flag,
  autonomous-send request (send-side must stay gated), PII leak via
  channel-comment excerpt.
- `backend/src/agents/seed_data/telegram_creator_v1.py` — seed:
  `master` (role_category=`master`, no tools) + `community-manager`
  (role_category=`communicator`, `tools_allowed=["telegram_read_updates",
  "telegram_draft_message"]`) + reused horizontal specialists (verbatim,
  mirrors `agency_marketing_ru_v1.ensure_agency_marketing_ru_seed`).
- `backend/tests/agents/test_seed_telegram_creator.py`,
  `test_telegram_creator_master_prompt.py`,
  `test_telegram_creator_golden_dataset.py` — unit coverage (no live LLM
  calls; no DB/testcontainers).

### Known gaps (explicitly out of scope this phase)

- `team_provisioning_service.py` does not yet route `preset_slug ==
  "telegram-creator"` to `ensure_telegram_creator_seed` (it only special-cases
  `agency-marketing-ru`) — needed before the product UI can provision this
  team end-to-end, but **not** required for the evaluator run (which calls
  `load_master_prompt` + `build_master_plan_agent`/`build_master_synthesis_agent`
  directly, same as `scripts/live_golden_master.py` does for
  `agency_marketing_ru`).
- Live evaluator-run (30-task golden-dataset + 5 adversarial scored by
  LLM-as-judge against the live model) — founder/evaluator-role step, not run
  this phase.
- Founder personal-operating-expertise edit (Pattern-D step 2) — not done this
  phase; this is the AI-baseline pass only.
- Friend-loop validation (Wave 1→2 gate) — not started.

### Reviewers

- _pending_ — founder review scheduled after this AI-baseline lands.

### Notes

- Mirrors the structural + procedural pattern of `agency-marketing-ru` (first
  Wave-1 vertical, Phase 01.2) exactly, per the autonomous-runner brief for
  Phase 01.10.
- All factual claims backed by cited web sources in `domain-brief.md`
  (accessed 2026-07-09) — no live LLM calls were made to produce any artifact
  in this vertical this phase.
