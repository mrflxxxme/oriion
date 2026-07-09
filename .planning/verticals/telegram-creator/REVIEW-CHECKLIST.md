---
title: "Telegram-крейтор — Founder Review Checklist"
vertical_slug: telegram_creator
version: 0.1.0
last-updated: 2026-07-09
status: draft
applies-to: prompts/* (master, community-manager) + golden-dataset/*
---

# Telegram-крейтор Review Checklist

> Используется founder'ом (или evaluator-role) перед promotion prompt'а от
> `draft` к `reviewed` (per P-INIT-4 + ADR-026 §3-4). Mirrors
> [`verticals/wb-seller/REVIEW-CHECKLIST.md`](../wb-seller/REVIEW-CHECKLIST.md)
> structure. Каждый блок — gate. Failed block ⇒ revisions needed OR escalate.

## 0. Pre-review

- [ ] Frontmatter complete и валиден YAML (per [DECISION-11](../../decisions/ADR-028-policies-registry.md#decision-11))
- [ ] `version` правильно incremented (SemVer per ADR-010)
- [ ] All factual claims содержат source citation (см. [`domain-brief.md`](./domain-brief.md))
- [ ] Tone matches Telegram-creator insider voice (Russian, не «AI claim» язык)
- [ ] `agent_archetype_slug` / `role_id` сопоставим с записью в `contracts/agents/` / seed (`telegram_creator_v1.py`)

## 1. Factual accuracy (Level B per ADR-026 §3)

- [ ] Terminology корректна (cross-check с [`domain-glossary.md`](./domain-glossary.md))
- [ ] Монетизационные цифры помечены как market-reference-range, не гарантия (domain-brief §4)
- [ ] РКН-реестр блогеров (10K+ триггер, 10 рабочих дней) корректно описан
- [ ] Маркировка рекламы (ФЗ-38, ОРД, erid, ЕРИР) корректно описана
- [ ] ERR-бенчмарки (10-30% <10K, 5-15% 10K-100K) не устарели относительно source
- [ ] No hallucinated Telegram-features / API endpoints / metric formulas
- [ ] Cross-references к контрактам (`contracts/*`) валидны и не сломаны

## 2. Operational realism

- [ ] Generated artifacts достижимы через реальный Telegram-workflow (ручная публикация; `send_telegram` — Wave 2 approval-gate, НЕ этот phase)
- [ ] Community-manager `tools_allowed` ограничен READ + DRAFT (`telegram_read_updates`, `telegram_draft_message`) — не включает `send_telegram`
- [ ] Cost-per-task оценка сходится с `.claude/agents/_shared/cost-budget.yaml`
- [ ] Memory-write patterns не создают PII-утечек (читательские DM/комментарии — anonymize)

## 3. Quality gates

- [ ] **Evaluator gate (golden-dataset)**: ≥ 75% pass-rate
- [ ] **Evaluator gate (adversarial)**: **100% pass-rate** (hard requirement)
- [ ] **Friend-loop** (Wave 1+): 3-5 ICP-friends ≥ 80% ✅ rating
- [ ] Frontmatter `golden-dataset-pass-rate` / `adversarial-probes-pass-rate` заполнены актуальными значениями
- [ ] Frontmatter `verified-by` содержит ≥ 1 entity (founder OR evaluator-role)

## 4. Compliance

- [ ] No PII в examples (anonymize подписчиков/комментаторов/DM-содержимое)
- [ ] Russian-only consumer-facing copy (за исключением брендов/международных терминов)
- [ ] No misleading claims об аффилиации с Telegram (мы — third-party tool, не Telegram-partner)
- [ ] No финансовых/налоговых консультаций от лица продукта (только операционные рекомендации; самозанятость упоминается описательно, не как совет)
- [ ] No medical / pharma / alcohol / weapon / 18+ content без явного user-flag

## 5. Anti-hallucination signals

- [ ] Prompt явно instructs «не знаю точно — скажи прямо» при неопределённости
- [ ] No invented Telegram-features (несуществующие форматы/API)
- [ ] Monetization ranges явно помечены как источник + дата (domain-brief)
- [ ] `hallucination-flags` frontmatter заполнен честно

## 6. Versioning & changelog

- [ ] `changelog.md` updated с описанием изменений
- [ ] Breaking changes — отдельная нотация + migration notes
- [ ] `next-verification` дата установлена (≤ 90 days вперёд) — особенно важно для РКН/ФЗ-38 положений, которые меняются чаще, чем платформенные факты

## Verdict

- ✅ **promoted** — frontmatter `status: reviewed`, artifact ready к archetype-publication
- 🔄 **revisions needed** — создать revision file с list of issues
- 🚨 **escalate** — factual / compliance / safety critical issue → halt + founder-only review

## Audit trail

- Каждый review запись добавляется в `changelog.md`
- Reviewer (founder name OR evaluator-role) + дата + verdict + key-findings

## References

- [ADR-026 §3-4](../../decisions/ADR-026-vertical-expertise-pipeline.md) — anti-hallucination protocol (+ §7 research-first amendment)
- [DECISION-11](../../decisions/ADR-028-policies-registry.md#decision-11) — frontmatter contract
- [`golden-dataset/README.md`](./golden-dataset/README.md) — evaluator methodology
- [`verticals/wb-seller/REVIEW-CHECKLIST.md`](../wb-seller/REVIEW-CHECKLIST.md) — structural template
