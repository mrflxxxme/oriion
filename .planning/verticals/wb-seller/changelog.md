---
title: "WB-Seller Vertical — Changelog"
vertical_slug: wb-seller
last-updated: 2026-05-13
---

# WB-Seller Vertical — Changelog

## 0.1.0 — 2026-05-13 — Initial skeleton (Milestone B.3)

### Added

- Vertical directory structure per [ADR-026 §2](../../decisions/ADR-026-vertical-expertise.md)
- `README.md` — ICP / JTBD / KPI overview
- `domain-glossary.md` — 40+ WB-specific terms (артикул, FBO/FBS, выкуп, СПП, etc.)
- `workflow-dag.md` — 3-agent coordinator/researcher/writer DAG for 5 primary tasks
- `kpis.md` — Wave-by-Wave business metrics aligned с ADR-025 gates
- `REVIEW-CHECKLIST.md` — founder + evaluator review gates (P-INIT-4)
- `golden-dataset/README.md` — LLM-as-judge evaluation methodology
- `prompts/coordinator.md` — initial coordinator system-prompt (draft, ready for evaluator)
- `prompts/researcher.md` — **SKELETON** (full body deferred to Milestone C Phase 00.5)
- `prompts/listing_writer.md` — **SKELETON** (full body deferred to Milestone C Phase 00.5)
- `golden-dataset/tasks/.gitkeep` — placeholder for 30 tasks

### Deferred to Milestone C Phase 00.5

- 30 golden-dataset tasks (10 easy / 15 medium / 5 hard)
- Adversarial probes set (≥ 5 per ADR-026 §3) with 100% pass-rate gate
- Full materialization `researcher.md` body (data-gathering protocol + WB-specific tool calls)
- Full materialization `listing_writer.md` body (copywriting templates + tone-control)
- Friend-loop validation (Wave 1) — after Wave 0 internal demo

### Reviewers

- _pending_ — founder review scheduled for Milestone C Phase 00.5

### Notes

- Founder = real-world expert WB-Seller (per [R-29](../../decisions/ADR-028-policies-registry.md#p-init-5) closure rationale)
- Tone in this vertical is calibrated to insider voice, не "AI claim"
- All factual claims to be backed by Wildberries Help Center + Partner Portal + founder operating expertise
