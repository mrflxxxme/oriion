# Roadmap Index — карта Wave / Phase

> Точка навигации по всему roadmap'у.

## Wave-обзор

| Wave | Срок | Цель | Документ | Метрика успеха |
|---|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: WB-Селлер team end-to-end | [wave-0/README.md](./wave-0-foundation/README.md) | Internal demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha с 3 vertical-templates + memory + billing + RBAC | [wave-1/README.md](./wave-1-core-mvp/README.md) | 10-15 friends, ≥3 задачи/клиент, success ≥75% |
| **2. Pixel + каталог** | 8 нед | Public beta: 5 vertical-templates + Pixel + Pyodide + MCP-каталог + core autonomy | [wave-2/README.md](./wave-2-pixel-catalog/README.md) | 100 регистраций/нед, TTFV ≤3 мин, конверсия ≥5% |
| **3. Глубина** | 8 нед | GA: Vertical Rituals + «Знания команды» + corp connectors + CS | [wave-3/README.md](./wave-3-depth/README.md) | 500 платящих, MRR ≥3 млн ₽ |
| **4. Масштаб + Partner** | 12 нед | K8s + Partner programme + dedicated namespace Pro + Anthropic/OpenAI proxy | [wave-4/README.md](./wave-4-scale-partner/README.md) | 2000 платящих, MRR ≥15 млн ₽ |
| **5+. Enterprise & v2** | 12+ мес | On-premise + Firecracker + open marketplace | [wave-5/README.md](./wave-5-enterprise/README.md) | TBD |

## Cross-Wave dependencies

```
Wave 0 (Foundation)
  ├─ Phase 00.1 (repo+CI) ──→ всё остальное Wave 0
  ├─ Phase 00.2 (auth) ─────→ зависят все Wave 1+
  ├─ Phase 00.3 (DB+Cell) ──→ зависят все Wave 1+
  ├─ Phase 00.4 (LLM-gateway) ──→ зависят все agent-фазы
  ├─ Phase 00.5 (WB team) ──→ зависят все vertical-фазы
  └─ Phase 00.6 (deploy) ──→ зависят все public-релизы

Wave 1 (Core MVP) — после Wave 0 done
Wave 2 (Pixel + каталог) — после Wave 1 done
Wave 3 (Глубина) — после Wave 2 GA
Wave 4 (Масштаб) — после Wave 3 metrics достигнуты
Wave 5+ (Enterprise) — после Wave 4 + enterprise customer
```

## Текущая phase

См. [`../STATUS.md`](../STATUS.md) для активной phase и blockers.

## Phase-files structure (per wave)

Каждый wave directory содержит:

```
wave-N-name/
├── README.md          ← цель wave, метрики, scope, sprint-план
├── PHASES.md          ← список phase'ов с короткими описаниями
└── phases/
    ├── N.1-slug.md    ← spec фазы N.1
    ├── N.2-slug.md    ← ...
    └── ...
```

## Phase-file conventions

Каждый phase-spec содержит:
- **Goal** (1 sentence)
- **Dependencies** (что должно быть готово)
- **Tasks** (список с estimates)
- **Acceptance criteria** (testable)
- **Risks** (ссылки на R-NN из risks-register)
- **ADR-refs** (ссылки на decisions)
- **Owner** (person или роль)
- **Status** (Pending / In Progress / Done / Blocked)

## Cross-references

- **Phase → ADR:** каждая phase ссылается на relevant ADR
- **Phase → Risk:** каждая phase ссылается на R-NN, которые она mitigate'ит
- **Phase → MCP-server / Vertical-template:** для Wave 2+ ссылки на specific deliverables

## Cheat sheet

| Сценарий | Куда смотреть |
|---|---|
| «Какая phase сейчас активна?» | [STATUS.md](../STATUS.md) |
| «Что в Wave N?» | `wave-N-name/README.md` |
| «Spec для phase X?» | `wave-N-name/phases/N.M-slug.md` |
| «Каковы dependencies?» | Phase-spec → секция Dependencies |
| «Какие риски в этой phase?» | Phase-spec → секция Risks |
