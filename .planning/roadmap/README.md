# Roadmap — карта Wave / Phase

High-level навигация по дорожной карте. Phase-уровень детализирован только для активной + следующей волны.

## Wave-обзор (revision 2026-05-15)

| Wave | Срок | Цель | Документ | Метрика успеха |
|---|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: horizontal `productivity-core` team end-to-end («Market & content brief») | [wave-0/README.md](./wave-0-foundation/README.md) | Internal demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha: horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + Telegram Business API + memory + billing + RBAC | [wave-1/README.md](./wave-1-core-mvp/README.md) | 10–15 friends, ≥3 задачи/клиент, success ≥75% |
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
  └─ Phase 00.7 (frontend skeleton) ──→ зависят все UI-фазы

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

**Phase-spec'ы для будущих волн НЕ хранятся в репо** — генерируются JIT в начале волны через `gsd:plan-phase` под актуальную архитектуру. Wave 0 сейчас единственная wave с заполненной `phases/`.

## Phase-spec conventions

- **Goal** (1 sentence)
- **Dependencies** (что должно быть готово)
- **Tasks** (список с estimates)
- **Acceptance criteria** (testable)
- **Risks** (ссылки на R-NN из `risks/REGISTER.md`)
- **ADR-refs** (ссылки на `decisions/`)
- **Owner** (роль или persistent agent per ADR-023)
- **Status** (Pending / In Progress / Done / Blocked)

## Cheat sheet

| Сценарий | Куда смотреть |
|---|---|
| «Какая phase активна?» | [`../STATUS.md`](../STATUS.md) |
| «Что в Wave N?» | `wave-N-name/README.md` + `PHASES.md` |
| «Spec для Wave 0 phase X?» | `wave-0-foundation/phases/00.M-slug.md` |
| «Spec для Wave 1+ phase?» | Генерируется в начале волны через `gsd:plan-phase` |
| «Каковы dependencies?» | Phase-spec → секция Dependencies |
| «Какие риски в этой phase?» | Phase-spec → секция Risks |
