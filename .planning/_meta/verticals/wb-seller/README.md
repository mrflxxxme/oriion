---
title: "Vertical: WB-Seller (Wildberries Marketplace Seller)"
vertical_slug: wb-seller
status: Wave 0 draft (founder = real-world expert per R-29)
last-updated: 2026-05-13
version: 0.1.0
milestone: B.3 (skeleton) → C Phase 00.5 (full materialization)
---

# Vertical: WB-Seller

> **Контекст:** Founder = real-world expert WB-Seller (per R-29 closure rationale в Milestone A).
> Tone in WB-Seller контенте — knowledgeable insider, не «AI claim». Используем точную WB-терминологию.

## ICP (Ideal Customer Profile)

- **Тип:** Индивидуальный предприниматель или малая компания (1-5 человек), продающие на Wildberries
- **Каталог:** 10-500 SKU, средний чек ₽1000-15000
- **Доход:** 500K-15M ₽/мес GMV, маржа 15-35%
- **Боли:**
  - ручное управление каталогом
  - реактивный мониторинг рейтинга
  - неоптимальные карточки
  - опаздывают с акциями
  - неправильно работают с выкупом
  - страдают от блокировок и штрафов
- **Уровень tech-savvy:** умеет пользоваться WB Personal Cabinet, Excel, простыми SaaS-tools; не разработчик
- **Геолокация:** РФ (вкл. крупные города + регионы), русскоязычные

## JTBD (Jobs To Be Done)

1. **Поддержание актуальности карточек** — «когда WB меняет требования к описаниям/категориям, я хочу автоматически обновить все SKU, чтобы не получить штрафы и не потерять видимость»
2. **Оптимизация листинга** — «когда я загружаю новый SKU, я хочу получить готовые title/description/keywords, оптимизированные под WB-поиск, чтобы конкурировать с большими селлерами»
3. **Реакция на отзывы и вопросы** — «когда покупатели задают вопросы или оставляют отзывы, я хочу отвечать в течение часа, чтобы поддерживать рейтинг и conversion»
4. **Мониторинг рейтинга и выкупа** — «когда мой выкуп проваливается ниже 70% или рейтинг падает ниже 4.5, я хочу получить алерт и actionable рекомендации»
5. **Подготовка к акциям** — «когда стартует распродажа (11.11, Чёрная пятница, дни рождения WB), я хочу автоматически готовить ценовые предложения и убедиться, что остатки достаточны»

## KPI summary

Детальные пороги — см. [`kpis.md`](./kpis.md).

| Wave | TTFV | Task success-rate | NPS | Pricing |
|------|------|-------------------|-----|---------|
| 0 (internal) | < 30 мин | ≥ 0.80 | n/a | n/a |
| 1 (friend-loop) | < 30 мин (3/5), < 60 мин (5/5) | ≥ 0.85 | ≥ 30 | ₽3000-7000/мес validated |
| 2 (public beta) | ≤ 3 мин median | (см. activation метрики) | track | conversion ≥ 5% week-4 |
| 3+ | — | — | ≥ 40 | ≥ 500 paying customers |

## Primary tasks (entry-point capabilities Wave 0)

1. **Generate listing** — title + description + keywords для нового SKU
2. **Audit existing listing** — против best-practice checklist
3. **Draft answer** — ответ на customer question
4. **Draft review-response** — ответ на негативный отзыв
5. **Snapshot ranking** — snapshot позиции + suggest improvements

## Agent team (vertical-level)

| Agent | Archetype slug | Role |
|-------|---------------|------|
| Coordinator | `wb-coordinator` | оркестратор: декомпозирует user-intent в task chain |
| Researcher | `wb-researcher` | собирает WB-specific data (категория rules, конкуренты, актуальные требования) |
| Listing Writer | `wb-listing-writer` | генерирует копи для cards / answers / reviews с tone-of-voice control |

Полный DAG взаимодействия — см. [`workflow-dag.md`](./workflow-dag.md).

## Cross-context dependencies

- [`_meta/contracts/agents/`](../../contracts/agents/) — `agent_archetypes` table хранит metadata прoмптов
- [`_meta/contracts/tasks/`](../../contracts/tasks/) — task lifecycle + CloudEvents
- Phase 00.5 (Milestone C) — WB-Seller team is shipped как Wave 0 acceptance criteria

## Anti-hallucination posture (per ADR-026 §3-4)

- **Level B** (verified-sources frontmatter, golden-dataset evaluator gate) — required для всех prompts перед promotion to `reviewed`
- **Level C** (friend-loop validation) — required для Wave 1→2 gate
- Adversarial probes: **100% pass-rate** — hard requirement

## References

- [ADR-026](../../decisions/ADR-026-vertical-expertise.md) — vertical-expertise architecture
- [DECISION-6](../GRILL-DECISIONS-ORIION.md#decision-6) — vertical Pattern D + founder = real expert WB-Seller
- [R-29](../GRILL-DECISIONS-ORIION.md#r-29) — closed (founder expertise as Level-B foundation)
- [DECISION-11](../GRILL-DECISIONS-ORIION.md#decision-11) — frontmatter contract
- [Phase 00.5](../../roadmap.md) — Milestone C deliverable

## Status & next steps

- ✅ Skeleton structure (Milestone B.3)
- ⏳ Full materialization of `prompts/researcher.md` + `prompts/listing_writer.md` — Milestone C Phase 00.5
- ⏳ 30 golden-dataset tasks — Milestone C Phase 00.5
- ⏳ Founder review checkpoint — Milestone C Phase 00.5
- ⏳ Friend-loop Wave 1 — после Wave 0 internal demo
