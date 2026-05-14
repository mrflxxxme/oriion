# Roadmap — карта Wave / Phase

High-level навигация по дорожной карте. Phase-уровень детализирован только для активной + следующей волны.

## Wave-обзор

| Wave | Срок | Цель | Документ | Метрика успеха |
|---|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: WB-Селлер team end-to-end | [wave-0/README.md](./wave-0-foundation/README.md) | Internal demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha с 3 vertical-templates + memory + billing + RBAC | [wave-1/README.md](./wave-1-core-mvp/README.md) | 10–15 friends, ≥3 задачи/клиент, success ≥75% |
| **2. Pixel + каталог** | 8 нед | Public beta: 5 vertical-templates + Pixel + Pyodide + MCP-каталог | [wave-2/README.md](./wave-2-pixel-catalog/README.md) | 100 регистраций/нед, TTFV ≤3 мин, конверсия ≥5% |
| **3. Глубина** | 8 нед | GA: Vertical Rituals + «Знания команды» + corp connectors + CS | [wave-3/README.md](./wave-3-depth/README.md) | 500 платящих, MRR ≥3 млн ₽ |
| **4. Масштаб + Partner** | 12 нед | K8s + Partner programme + dedicated namespace Pro | [wave-4/README.md](./wave-4-scale-partner/README.md) | 2000 платящих, MRR ≥15 млн ₽ |
| **5+. Enterprise & v2** | 12+ мес | On-premise + Firecracker + open marketplace | [wave-5/README.md](./wave-5-enterprise/README.md) | TBD |

## Cross-Wave dependencies

```
Wave 0 (Foundation)
  ├─ Phase 00.1 (repo+CI) ──→ всё остальное Wave 0
  ├─ Phase 00.2 (auth) ─────→ зависят все Wave 1+
  ├─ Phase 00.3 (DB+Cell) ──→ зависят все Wave 1+
  ├─ Phase 00.4 (LLM-gateway) ──→ зависят все agent-фазы
  ├─ Phase 00.5 (WB team) ──→ зависят все vertical-фазы
  ├─ Phase 00.6 (deploy) ──→ зависят все public-релизы
  └─ Phase 00.7 (frontend skeleton) ──→ зависят все UI-фазы

Wave 1 → после Wave 0 done
Wave 2 → после Wave 1 done
Wave 3 → после Wave 2 GA
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
