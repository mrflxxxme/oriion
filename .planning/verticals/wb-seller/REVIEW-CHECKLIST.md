---
title: "WB-Seller — Founder Review Checklist"
vertical_slug: wb-seller
version: 0.1.0
last-updated: 2026-05-13
status: draft
applies-to: vertical-prompts/* (coordinator, researcher, listing_writer) + golden-dataset/*
---

# WB-Seller Review Checklist

> Используется founder'ом перед promotion prompt'а от `draft` к `reviewed` (per P-INIT-4 + ADR-026 §3-4).
> Каждый блок — gate. Failed block ⇒ revisions needed OR escalate.

## 0. Pre-review

- [ ] Frontmatter complete и валиден YAML (per [DECISION-11](../../decisions/ADR-028-policies-registry.md#decision-11) contract)
- [ ] `version` правильно incremented (semver)
- [ ] All factual claims содержат source citation (URL + accessed-date)
- [ ] Tone matches WB-Seller insider voice (Russian, informal-professional, без AI-claim языка)
- [ ] `agent_archetype_slug` сопоставим с записью в `contracts/agents/` table

## 1. Factual accuracy (Level B per ADR-026 §3)

- [ ] WB-specific terminology корректна (cross-check с [`domain-glossary.md`](./domain-glossary.md))
- [ ] Цитированные правила WB актуальны (`accessed` дата в frontmatter < 90 days)
- [ ] No hallucinated WB tools / API endpoints / metric formulas
- [ ] No outdated promo dates / pricing tiers / fee structures (комиссия, эквайринг, СПП)
- [ ] Cross-references к контрактам (`contracts/*`) валидны и не сломаны
- [ ] Category-specific правила (например, размерная сетка для одежды) корректны для упомянутых категорий

## 2. Operational realism

- [ ] Generated artifacts достижимы через WB Personal Cabinet UX OR API (Wave 1+)
- [ ] No требования к продавцу делать невозможное (e.g., модифицировать WB-internal ranking logic)
- [ ] Recommended actions feasible в текущем WB регуляторном field
- [ ] Cost-per-task оценка сходится с `_shared/cost-budget.yaml` guardrails
- [ ] Memory-write patterns не создают PII-утечек

## 3. Quality gates

- [ ] **Evaluator gate (golden-dataset)**: ≥ 75% pass-rate (Wave 0)
- [ ] **Evaluator gate (adversarial)**: **100% pass-rate** (per ADR-026 §3 hard requirement)
- [ ] **Friend-loop** (Wave 1+): 3-5 ICP-friends ≥ 80% ✅ rating (subjective)
- [ ] Frontmatter `golden-dataset-pass-rate` и `adversarial-probes-pass-rate` заполнены актуальными значениями
- [ ] Frontmatter `verified-by` содержит ≥ 1 entity (founder OR external SME)

## 4. Compliance

- [ ] No PII в examples (anonymize SKU IDs, seller IDs, customer names)
- [ ] Russian-only consumer-facing copy (за исключением brand-names, technical SKU codes)
- [ ] No misleading claims о relationships с WB (мы — third-party seller-tool, не WB-affiliate)
- [ ] No legal advice (e.g., налоги, регистрация ИП, споры с WB — only operational ops)
- [ ] No medical / pharma / alcohol / weapon / 18+ content в generated artifacts без явного user-flag

## 5. Anti-hallucination signals

- [ ] Prompt явно instructs "say I don't know" при неопределённости (no over-confidence)
- [ ] No invented WB-features (например, несуществующие promo-инструменты)
- [ ] No outdated WB-screenshots / UI-references
- [ ] `hallucination-flags` frontmatter заполнен честно (известные edge cases)

## 6. Versioning & changelog

- [ ] `changelog.md` updated с описанием изменений
- [ ] Breaking changes (если есть) — отдельная нотация + migration notes
- [ ] `next-verification` дата установлена (≤ 90 days вперёд)

## Verdict

- ✅ **promoted** — frontmatter `status: reviewed`, artifact ready к archetype-publication
- 🔄 **revisions needed** — создать revision file с list of issues
- 🚨 **escalate** — factual / compliance / safety critical issue → halt + founder-only review

## Audit trail

- Каждый review запись добавляется в `changelog.md`
- Reviewer (founder name OR external SME) + дата + verdict + key-findings
- Если verdict ≠ ✅ — link to revision-task

## References

- [ADR-026 §3-4](../../decisions/ADR-026-vertical-expertise.md) — anti-hallucination protocol
- [DECISION-11](../../decisions/ADR-028-policies-registry.md#decision-11) — frontmatter contract
- [P-INIT-4](../../roadmap.md) — review checkpoint phase
- [`golden-dataset/README.md`](./golden-dataset/README.md) — evaluator methodology
