---
title: "Vertical: Telegram-крейтор (RU Telegram content creator)"
vertical_slug: telegram_creator
preset_slug: telegram-creator
status: draft — Wave 1 (AI-baseline, awaiting founder review)
last-updated: 2026-07-09
version: 0.1.0
milestone: Phase 01.10 (second Wave-1 vertical per ADR-017)
---

# Vertical: Telegram-крейтор

> **Research-first note:** this vertical's ICP/JTBD/domain facts are grounded in
> [`domain-brief.md`](./domain-brief.md) (cited web research, per the ADR-026
> §7 research-first amendment). Read it first — everything below is a
> product-shaped distillation of that brief, not new claims.

Second Wave-1 vertical per [ADR-017](../../decisions/ADR-017-vertical-templates.md)
catalog entry #2 ("Telegram-крейтор / Курс-автор"), built on top of the
horizontal `productivity-core` team with a Master-Agent layer per
[ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md), mirroring
the first Wave-1 vertical, `agency-marketing-ru` ([`verticals/agency-marketing-ru/`](../agency-marketing-ru/)).

## ICP (Ideal Customer Profile)

- **Тип:** автор Telegram-канала — от микро-крейтора (1-10K подписчиков) до
  established-крейтора (100K+); большинство ведёт **личный/авторский канал**
  под своим именем, не безликий агрегатор (Telemetr 2024, см. domain-brief §1).
- **Монетизация:** часто уже пробует и/или совмещает несколько моделей —
  спонсорские посты, Telegram Stars (платная подписка/платные посты), участие
  в Яндекс.РСЯ-программе, продажа собственного продукта (курс/консультации).
- **Команда:** у большей части монетизирующихся авторов — команда 2+ человек
  (автор + редактор/SMM), не соло — что и обуславливает ценность
  Coordinator→specialists делегирования, а не только single-user tool.
- **Налоговый статус:** самозанятость (НПД) — не юрлицо; продукт не даёт
  юридических/налоговых консультаций, только операционные рекомендации.
- **Гео/язык:** РФ, русскоязычные; контент — русский язык (кроме
  международных терминов/брендов).

## JTBD (Jobs To Be Done)

1. **Контент-план без выгорания** — «когда я не знаю, что публиковать сегодня,
   я хочу получить рубрику + черновик поста, чтобы держать ритм канала».
2. **Репёрпоузинг** — «когда у меня есть один инсайт/кейс, я хочу превратить
   его в пост + сторис + фоллоу-ап без повторной работы с нуля».
3. **Понятная аналитика** — «когда я смотрю статистику (ERR, охваты), я хочу
   получить понятную интерпретацию относительно бенчмарка моего размера
   канала, а не сырые цифры».
4. **Монетизация без косяков с законом** — «когда я беру спонсорский пост или
   запускаю платную подписку, я хочу быть уверен, что маркировка рекламы и
   РКН-требования соблюдены».
5. **Не терять читателей** — «когда вовлечённость падает, я хочу понять,
   почему, и получить план восстановления, а не общие советы».

## KPI summary

Детальные пороги — см. [`kpis.md`](./kpis.md).

| Wave | TTFV | Task success-rate | NPS | Pricing |
|------|------|--------------------|-----|---------|
| 1 (friend-loop) | < 30 мин (3/5), < 60 мин (5/5) | ≥ 0.85 | ≥ 30 | ₽2000-6000/мес (creator tier) |
| 2 (public beta) | ≤ 3 мин median | (см. activation) | track | conversion ≥ 5% week-4 |
| 3+ | — | — | ≥ 40 | часть общего MRR-таргета |

## Primary tasks (entry-point capabilities)

1. **Контент-план** — рубрикатор + черновики постов на период (неделя/месяц)
2. **Написание поста** — черновик поста в заданном формате/рубрике/тоне
3. **Аудит канала / аналитика** — интерпретация метрик (ERR, охваты, отток)
   относительно бенчмарка размера канала
4. **Комплаенс-аудит** — проверка спонсорского поста на маркировку рекламы
   (ОРД/erid) + РКН-реестр блогеров (10K+ триггер)
5. **Стратегия монетизации + репёрпоузинг** — выбор модели монетизации под
   размер/нишу канала + план адаптации контента под форматы

## Agent team (vertical-level)

| Agent | Archetype slug | Role | Reused from horizontal? |
|-------|----------------|------|--------------------------|
| Master | `master` (vertical=`telegram_creator`) | доменный CEO — стратегическая цель + доменные ограничения (РКН/ад-маркировка/монетизация) + финальный синтез | нет — vertical-specific |
| Coordinator | `coordinator` | операционный COO — декомпозиция + делегирование | да (horizontal, verbatim) |
| Researcher | `researcher` | сбор данных (тренды, конкуренты, аналитика канала) | да (horizontal, verbatim) |
| Writer | `writer` | черновики постов/сторис/фоллоу-апов | да (horizontal, verbatim) |
| Analyst | `analyst` | интерпретация метрик (ERR, охваты) | да (horizontal, verbatim) |
| Community-manager | `community-manager` (vertical=`telegram_creator`) | читает активность канала (`telegram_read_updates`) и готовит platform-native черновики (`telegram_draft_message`) — **read+draft only, без автономной отправки** | нет — vertical-specific |

Полный DAG взаимодействия — см. [`workflow-dag.md`](./workflow-dag.md).

## Connector tools (01.9b, ADR-041)

`community-manager`'s `tools_allowed` lists the two Telegram-bot connector
tools already classified in
[`src/security/capability.py`](../../../backend/src/security/capability.py)
`TOOL_RISK`:

| Tool | Risk tier | What it does |
|------|-----------|--------------|
| `telegram_read_updates` | READ_ONLY | reads channel/bot updates (comments, reactions, DMs) — no side-effect |
| `telegram_draft_message` | INTERNAL | prepares a message draft artifact — no outward action |
| `send_telegram` (paired, NOT in this vertical's `tools_allowed`) | DANGEROUS | actually posts — deny-until-approval-UI (01.12); explicitly out of scope for this phase |

This matches the domain scope: **read + draft only, no autonomous posting** —
send-side capability activates once the approval-UI (01.12) ships.

## Cross-context dependencies

- [`contracts/agents/`](../../contracts/agents/) — `agent_archetypes` table stores archetype metadata
- [`contracts/role-prompts/masters/telegram_creator.md`](../../contracts/role-prompts/masters/telegram_creator.md) — the canonical Master-prompt (loaded by `src.agents.services.role_prompt_loader.load_master_prompt`)
- [`backend/src/agents/seed_data/telegram_creator_v1.py`](../../../backend/src/agents/seed_data/telegram_creator_v1.py) — the seed (Master + community-manager + reused horizontal)
- [`src/security/capability.py`](../../../backend/src/security/capability.py) — `TOOL_RISK` classification for the connector tools above

## Out of scope (this phase, Phase 01.10)

- Live evaluator-run (LLM-as-judge scoring the golden-dataset) — a separate,
  founder/evaluator-role-orchestrated step (per ADR-026 Pattern-D step 3).
- Telegram Business API (native CRM-style features) — Wave 2+ per ADR-017.
- Telegram Mini App — Wave 2 per ADR-017.
- Live Bot-API demo / actual `send_telegram` wiring — gated to the 01.12
  approval-UI.
- Founder review / promotion `draft → reviewed` — founder-owned step.

## Anti-hallucination posture (per ADR-026 §3-4)

- **Level B** (verified-sources frontmatter, golden-dataset evaluator gate) —
  required for all prompts before promotion to `reviewed`.
- **Level C** (friend-loop validation) — required for Wave 1→2 gate.
- Adversarial probes: **100% pass-rate** — hard requirement.
- Monetization figures (subscriber-tier revenue ranges) are **market reference
  ranges from secondary sources**, never per-creator guarantees — see
  domain-brief §4.

## References

- [`domain-brief.md`](./domain-brief.md) — cited research (ADR-026 §7 research-first step)
- [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md) — vertical-expertise architecture (+ §7 research-first amendment)
- [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md) — Master-Agent layer
- [ADR-017](../../decisions/ADR-017-vertical-templates.md) — 5 vertical-templates catalog (entry #2)
- [ADR-010](../../decisions/ADR-010-role-versioning.md) — prompt SemVer policy
- [`verticals/agency-marketing-ru/`](../agency-marketing-ru/) — the first Wave-1 vertical (Phase 01.2), the structural reference this vertical mirrors

## Status & next steps

- ✅ `domain-brief.md` — cited AI-baseline research (this phase)
- ✅ Skeleton structure + full doc set (this phase, mirroring `wb-seller/`)
- ✅ Master-prompt (draft, `contracts/role-prompts/masters/telegram_creator.md`)
- ✅ `community-manager` role-prompt (draft, vertical-specific)
- ✅ 30 golden-dataset tasks + 5 adversarial probes (AI-baseline)
- ✅ Seed (`telegram_creator_v1.py`) — Master + community-manager + reused horizontal
- ⏳ Founder review (personal operating expertise edit, Pattern-D step 2)
- ⏳ Live evaluator-run → promote `draft → reviewed` (founder/evaluator-role step)
- ⏳ Friend-loop validation (Wave 1→2 gate)
- ⏳ `team_provisioning_service.py` preset-routing wire-up (not needed for the
  evaluator run — see `changelog.md` — but required before the product UI can
  provision this preset end-to-end)
