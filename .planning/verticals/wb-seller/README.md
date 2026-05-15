---
title: "Vertical: WB-Seller (Wildberries Marketplace Seller)"
vertical_slug: wb-seller
status: deferred to Wave 2 (per Session-2026-05-15 reorg)
last-updated: 2026-05-15
version: 0.1.0
milestone: legacy W0-targeting → Wave 2 alignment pending
---

# Vertical: WB-Seller

> **⚠️ Status revision 2026-05-15:** WB-Seller vertical-template moved from Wave 0 anchor → Wave 2 per [ADR-017 revision](../../decisions/ADR-017-vertical-templates.md) + Session-2026-05-15.
>
> **Architectural alignment pending Wave 2 Phase 02.X (WB-vertical materialization).** Все материалы в этой директории — prompts/, golden-dataset/, kpis.md, workflow-dag.md — построены под прежнюю архитектуру (Coordinator-only, без Master-Agent). При materialize в Wave 2 потребуется:
> 1. **Добавить Master-Agent prompt** (`prompts/master.md`) per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md) — WB-Селлер CEO с domain-knowledge keeper-responsibilities.
> 2. **Адаптировать существующий `prompts/coordinator.md`** под subordinate-COO-mode (принимает strategic_context от Master).
> 3. **Реструктурировать workflow-dag.md** под layered orchestration (Master → Coordinator → specialists).
> 4. **Переосмыслить golden-dataset** — часть задач (research / qa / review) теперь обрабатывает horizontal Researcher/Writer (reused), часть — WB-specific Listing Writer + Master.
> 5. **Привести prompts к 9-секционной structure per `contracts/role-prompts/` pattern** для consistency с horizontal preset (Wave 0) и future verticals (W1).
>
> Текущее содержимое сохраняется как valuable prep-work (30 golden-dataset tasks + 5 adversarial probes, domain glossary, KPI thresholds, REVIEW-CHECKLIST) — все они переиспользуются после alignment.
>
> **Контекст:** Founder = real-world expert WB-Seller (per R-29 closure rationale в Milestone A). Tone in WB-Seller контенте — knowledgeable insider, не «AI claim». Используем точную WB-терминологию.

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

- [`contracts/agents/`](../../contracts/agents/) — `agent_archetypes` table хранит metadata прoмптов
- [`contracts/tasks/`](../../contracts/tasks/) — task lifecycle + CloudEvents
- Phase 00.5 (Milestone C) — WB-Seller team is shipped как Wave 0 acceptance criteria

## Anti-hallucination posture (per ADR-026 §3-4)

- **Level B** (verified-sources frontmatter, golden-dataset evaluator gate) — required для всех prompts перед promotion to `reviewed`
- **Level C** (friend-loop validation) — required для Wave 1→2 gate
- Adversarial probes: **100% pass-rate** — hard requirement

## References

- [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md) — vertical-expertise architecture
- [DECISION-6](../../decisions/ADR-028-policies-registry.md#decision-6) — vertical Pattern D + founder = real expert WB-Seller
- [R-29](../../decisions/ADR-028-policies-registry.md#p-init-5) — closed (founder expertise as Level-B foundation)
- [DECISION-11](../../decisions/ADR-028-policies-registry.md#decision-11) — frontmatter contract
- ~~Phase 00.5~~ → replaced by Wave 2 Phase 02.X (TBD) — Wave 2 WB-vertical-build phase per Session-2026-05-15. Wave 0 Phase 00.5 теперь = [`pydantic-ai-productivity-team`](../../roadmap/wave-0-foundation/phases/00.5-pydantic-ai-productivity-team.md) (horizontal preset).

## Status & next steps

- ✅ Skeleton structure (Milestone B.3)
- ✅ 30 golden-dataset tasks + 5 adversarial probes (preserved as Wave 2 prep)
- ✅ Existing prompts (coordinator / listing_writer / researcher) preserved as legacy W0-targeting materials
- ⏳ **Wave 2 alignment pending** per ADR-029 (Master-Agent layer) — Phase 02.X (TBD при старте Wave 2)
- ⏳ Public-beta ship — Wave 2 acceptance gate
