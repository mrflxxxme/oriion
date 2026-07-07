# Roadmap — карта Wave / Phase

High-level навигация по дорожной карте. Phase-уровень детализирован только для активной + следующей волны.

## Wave-обзор (revision 2026-05-15)

| Wave | Срок | Цель | Документ | Метрика успеха |
|---|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: horizontal `productivity-core` team end-to-end («Market & content brief») | [wave-0/README.md](./wave-0-foundation/README.md) | Internal demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha: horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + memory + billing + RBAC + MCP (Telegram Business API → parked, RW-05) | [wave-1/README.md](./wave-1-core-mvp/README.md) | Технические пороги per [gate wave-1-to-2](../gates/wave-1-to-2.md) (ADR-040 D5): AC pass-rate ≥0.9 + must-фазы merged; friend-метрики → W2 фаза 02.0 |
| **2. Pixel + каталог** | 9 нед | Public beta: 4 templates (horizontal + Marketing + Telegram + WB) + Pixel + Pyodide + Telegram Mini App + Master-Agent retrofit | [wave-2/README.md](./wave-2-pixel-catalog/README.md) | 100 регистраций/нед, TTFV ≤3 мин, конверсия ≥5% |
| **3. Глубина** | 10 нед | GA: +ИП-Бух + СМБ-Sales vertical с Master-Agent + Vertical Rituals + PARA Workspace + corp connectors + CS | [wave-3/README.md](./wave-3-depth/README.md) | 500 платящих, MRR ≥3 млн ₽ |
| **4. Масштаб + Partner** | 12 нед | K8s + Partner programme + dedicated namespace Pro + Telegram Stars billing | [wave-4/README.md](./wave-4-scale-partner/README.md) | 2000 платящих, MRR ≥15 млн ₽ |
| **5+. Enterprise & v2** | 12+ мес | On-premise + Firecracker + open marketplace | [wave-5/README.md](./wave-5-enterprise/README.md) | TBD |

### Team-presets distribution

| Preset | W0 | W1 | W2 | W3 | W4+ |
|---|---|---|---|---|---|
| 🧰 `productivity-core` (horizontal) | ✅ ship | hardening | extend | PARA-memory | — |
| 📈 `agency_marketing_ru` (vertical+Master) | — | ✅ ship | hardening | rituals | — |
| ✍️ `telegram_creator` (vertical+Master) | — | ✅ ship | +Mini App | rituals | — |
| 🛒 `wb_seller_v1` (vertical+Master) | — | — | ✅ ship | rituals | — |
| 💼 `accounting_ip` (vertical+Master) | — | — | — | ✅ ship | — |
| 🎯 `smb_sales_ru` (vertical+Master) | — | — | — | ✅ ship | — |

## Cross-Wave dependencies

```
Wave 0 (Foundation)
  ├─ Phase 00.1 (repo+CI) ──→ всё остальное Wave 0
  ├─ Phase 00.2 (auth) ─────→ зависят все Wave 1+
  ├─ Phase 00.3 (DB+Cell) ──→ зависят все Wave 1+
  ├─ Phase 00.4 (LLM-gateway) ──→ зависят все agent-фазы
  ├─ Phase 00.5 (productivity-core horizontal team) ──→ зависят все team-фазы
  ├─ Phase 00.6 (deploy) ──→ зависят все public-релизы
  ├─ Phase 00.7 (frontend skeleton) ──→ зависят все UI-фазы
  └─ Phase 00.8 (design restyling, ADR-031) ──→ visual base для 01.5 Dashboard UI + W2 brand refresh

Wave 1 → после Wave 0 done; первая инстанциация Master-Agent layer + Coordinator subordinate-mode retrofit
Wave 2 → после Wave 1 done; WB-vertical materialized; Pixel Department; Mini App
Wave 3 → после Wave 2 GA; ИП-Бух + СМБ-Sales verticals; Vertical Rituals
Wave 4 → после Wave 3 metrics достигнуты
Wave 5+ → после Wave 4 + enterprise customer
```

## Текущая phase

См. [`../STATUS.md`](../STATUS.md).

## Структура wave-папки

```
wave-N-name/
├── README.md          цель wave, метрики, scope, sprint-план
├── PHASES.md          список phase'ов с короткими описаниями
└── phases/            детальные phase-spec (ТОЛЬКО для активной + следующей волны)
    └── N.M-slug.md
```

**Phase-spec'ы для будущих волн НЕ хранятся в репо** — генерируются JIT в начале волны под актуальную архитектуру. **Ревизия per [ADR-040 D1](../decisions/ADR-040-execution-spec-contract.md):** JIT сохраняется, но (а) каждая фаза **текущей** волны имеет **seed-spec** (5–15 строк констрейнтов) в `phases/` уже при регенерации PHASES.md; (б) доросшая спека валидируется против [`DEFINITION-OF-READY.md`](./DEFINITION-OF-READY.md) до execute; (в) первая фаза каждой волны — обязательная `NN.1-retro`, погашающая [`DEFERRED-VERIFICATION.md`](../DEFERRED-VERIFICATION.md) (ADR-040 D6); (г) реорганизация roadmap обязана в том же PR синхронизировать затронутые `gates/*.md` (ADR-040 D5).

## Phase-spec conventions

Нормативный чек-лист полноты — [`DEFINITION-OF-READY.md`](./DEFINITION-OF-READY.md) (ADR-040 D1). Базовые секции:

- **Goal** (1 sentence, проверяемый исход)
- **Dependencies** (что должно быть готово; статус проверен по факту)
- **Founder-зависимости** (ссылки на [`FOUNDER-RUNWAY.md`](../FOUNDER-RUNWAY.md) или явное «нет»)
- **Scope / Out-of-scope** (границы; всё исключённое имеет адрес)
- **Acceptance criteria** (testable; мягкие AC → запись в DEFERRED-VERIFICATION до merge)
- **Evidence-гейты + live-golden бюджет** (только где контрольная ценность, ADR-040 D11)
- **Tripwire-прогноз** (категории `tripwire.yaml`, которые фаза заденет)
- **Risks** (ссылки на R-NN из `risks/REGISTER.md`)
- **ADR-refs** (ссылки на `decisions/`)
- **Status** (Pending / Parked / In Progress / Done / Blocked)

Wave-0-эра дополнительно имела Owner + Tasks-with-estimates — в автономном контуре (ADR-037/040) исполнитель = runner, декомпозиция живёт в `NN-PLAN.md`.

## Cheat sheet

| Сценарий | Куда смотреть |
|---|---|
| «Какая phase активна?» | [`../STATUS.md`](../STATUS.md) |
| «Что в Wave N?» | `wave-N-name/README.md` + `PHASES.md` |
| «Spec для Wave 0 phase X?» | `wave-0-foundation/phases/00.M-slug.md` |
| «Spec для Wave 1+ phase?» | Seed-spec в `phases/` текущей волны; дорастает на discuss-шаге, валидируется по [DoR](./DEFINITION-OF-READY.md) |
| «Фаза готова к автономному execute?» | [`DEFINITION-OF-READY.md`](./DEFINITION-OF-READY.md) — 11 пунктов, `DoR: PASS` в PLAN.md |
| «Что разблокирует parked-фазы?» | [`../FOUNDER-RUNWAY.md`](../FOUNDER-RUNWAY.md) |
| «Какой AC закрыт частично?» | [`../DEFERRED-VERIFICATION.md`](../DEFERRED-VERIFICATION.md) |
| «Каковы dependencies?» | Phase-spec → секция Dependencies |
| «Какие риски в этой phase?» | Phase-spec → секция Risks |
