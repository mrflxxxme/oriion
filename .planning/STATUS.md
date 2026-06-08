# STATUS — текущее состояние проекта

> Rolling-status. Обновляется при phase complete / blocker resolved / новом ADR.

## Wave-progress

| Wave | Status | Anchor target |
|---|---|---|
| Pre-Wave-0 | ✅ Complete | Roadmap reorg per [Session-2026-05-15](./JOURNAL.md) |
| Wave 0 (Foundation) | 🔄 **Closing** (all build phases ✅; architecture **live-validated locally**; only the founder staging 10× anchor run remains) | Horizontal `productivity-core` team — internal demo «Market & content brief» |
| Wave 1 (Core MVP) | ⏳ Pending — Phase 01.1 retro file created в PR-B C8 (AC-W1-1..17) | Horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + Telegram Business API |
| Wave 2 (Pixel + каталог) | ⏳ Pending | +WB-Селлер vertical + Pixel + Pyodide + Mini App + Master-Agent first-instances |
| Wave 3 (Глубина) | ⏳ Pending | +ИП-Бух + СМБ-Sales vertical + Vertical Rituals + PARA Workspace |
| Wave 4 (Масштаб) | ⏳ Pending | K8s + Partner programme + Telegram Stars billing |
| Wave 5+ (Enterprise) | ⏳ Pending | On-premise + open marketplace |

## Текущая активная фаза

**Phase 00.7 (Frontend skeleton)** — ⏳ **NEXT** (opens now; runs ∥ Wave-0 close per roadmap). UI поверх доказанного API.

**Phase 00.6 PR-B (Stage B + orchestrator-dispatch + live validation)** — ✅ **Complete** ([PR #38](https://github.com/mrflxxxme/oriion/pull/38) C0–C12 + [PR #39](https://github.com/mrflxxxme/oriion/pull/39) C13–C19, merged 2026-06-08). Full 5-agent retro PASS. **Архитектура доказана end-to-end на живом стеке с реальными LLM** (DeepSeek + live Brave + YandexGPT 5.1 Pro failover; AC8+AC10 PASS, AC9 matrix+plan PASS, brief-length = Wave-1 tuning). 7 deployment-багов найдено и починено живым прогоном (C13–C19). См. [`HANDOFF.md`](./HANDOFF.md).

**Оставшийся Wave-0 пункт:** founder staging 10× anchor run (gate D5 — `internal_demo_passed`) — Wave-0→Wave-1 gate, НЕ блокирует Phase 00.7. Runbook: `docs/runbooks/staging-bootstrap.md`.

**Phase 00.6 PR-A (Stage A local infra)** — ✅ **Complete** ([PR #36](https://github.com/mrflxxxme/oriion/pull/36); 22 commits; AC-W1-11..15).

## Phase history (Wave-0)

| Phase | Status | PR | Notes |
|---|---|---|---|
| Pre-Wave-0 roadmap reorg | ✅ Complete | (planning-only) | Session-2026-05-15 — 11 развилок resolved |
| Architect-PR (pre-00.2) | ✅ Complete | [#27](https://github.com/mrflxxxme/oriion/pull/27) | `_shared/0001_init.py` + extended iam contracts + 12 bounded-context migration dirs |
| 00.1 — Repo & CI/CD | ✅ Complete | [#25](https://github.com/mrflxxxme/oriion/pull/25), `b192c6b` | merged 2026-05-17 |
| 00.2 — Custom JWT auth | ✅ Complete | `[00.2] feat(iam)...` 2026-05-18 | src.iam coverage 86.69%, AC1-AC10 green |
| 00.2.5 — Integration | ✅ Complete | [#32](https://github.com/mrflxxxme/oriion/pull/32) 2026-05-19 | 8 commits; deleted `_stubs/` + rewired imports |
| 00.3 — DB+RLS+multitenancy | ✅ Complete | (parallel batch с 00.2 + 00.4) | |
| 00.4 — LLM gateway + MCP | ✅ Complete | (parallel batch с 00.2 + 00.3) | |
| 00.5 / 00.5a — Pydantic-AI runtime | ✅ Complete | merged 2026-05-20 | |
| 00.5b — runtime + tasks + orchestrator | ✅ Complete | [#35](https://github.com/mrflxxxme/oriion/pull/35) 2026-05-21 | 5-agent audit 3H/15M/17L; AC-W1-1..10 pin block |
| **00.6 PR-A** — Stage A local infra | ✅ Complete | [#36](https://github.com/mrflxxxme/oriion/pull/36) 2026-05-25 | 22 commits; self-audit 0H/9M/10L; AC-W1-11..15 pin block extension |
| **00.6 PR-B** — Stage B + orchestrator-dispatch + live validation | ✅ Complete | [#38](https://github.com/mrflxxxme/oriion/pull/38) + [#39](https://github.com/mrflxxxme/oriion/pull/39) 2026-06-08 | C0–C19; 5-agent retro PASS; architecture live-proven; AC-W1-16..23 |
| 00.7 — Frontend skeleton | ⏳ **NEXT** | TBD | opens now (∥ Wave-0 close); UI on proven API |

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

> **Note:** OQ-13/14/15/16 (hiring) закрыты как `N/A` per [P-INIT-5](./decisions/ADR-028-policies-registry.md#policies-canonical-home). OQ-17 (funding) + OQ-18 (burn-budget) закрыты как `out-of-scope` per Session-2026-05-15.

## Top-priority risks (active monitoring)

См. [`risks/REGISTER.md`](./risks/REGISTER.md).

1. R-04 (runaway costs) — high + high
2. R-05 (data leak) — critical + medium
3. R-08 (регуляторные изменения) — high + high
4. R-11 (retention/churn) — high + high
5. R-12 (scope creep) — critical + high

## Tech-стек snapshot

Полный список — [`_meta/stack.md`](./_meta/stack.md).

- Backend: Python 3.12 + FastAPI + Pydantic-AI 1.30.1
- Frontend: Vite 6 + React 19 + TanStack Router + Tailwind + shadcn/ui (skeleton in Phase 00.7)
- DB: PostgreSQL 16 + pgvector + Yandex Managed
- Cache: Redis 7 + Dramatiq (orchestrator-dispatch swap к Dramatiq tracked AC-W1-16)
- 2D: Native Canvas
- Code-exec: Pyodide WASM (browser)
- Auth: Custom JWT (W0–1) → Logto (W2–3) → Keycloak (Enterprise)
- LLM: DeepSeek V4-flash/V4-pro (ADR-018 amended in PR-B C6) + YandexGPT + GigaChat + BYOK
- Cloud: Yandex Cloud ru-central-1
- Observability (от Phase 00.6 PR-A): OpenTelemetry SDK + Prometheus 9-metric family + structlog OTel correlation + Loki + Tempo + Grafana 3 dashboards + Alertmanager 8 rules в 3 groups
- IaC (от Phase 00.6 PR-B): Terraform Yandex provider (VM + Managed PG + Redis + Lockbox + DNS + Object Storage)
- CI/CD (от Phase 00.6 PR-B): GitHub Actions deploy-staging workflow (build → push к YC CR → SSH → compose pull/up → wait_healthy → smoke → Grafana annotation, ≤10 min)

## Целевые сроки (revision 2026-05-15)

| Дата | Milestone | Delta vs prior |
|---|---|---|
| 2026-05-17 | Wave 0 Phase 00.1 **started + merged** (2 дня раньше plan) | **-2 нед** |
| 2026-05-26 | Wave 0 Phase 00.6 PR-B **in flight** | on track |
| 2026-06-09 | Wave 0 complete → Internal demo (horizontal `productivity-core`) | unchanged (Phase 00.6 PR-B 10× demo run + Phase 00.7 frontend ship → full anchor flip) |
| 2026-07-21 | Wave 1 complete → Pre-alpha с 10–15 friends (3 templates) | unchanged |
| ~2026-09-22 | Wave 2 complete → Public beta (4 templates + Pixel + Mini App) | **+1 нед** vs prior 2026-09-15 |
| ~2026-12-01 | Wave 3 complete → GA-release (6 templates + Rituals + PARA) | **+3 нед** vs prior 2026-11-10 |
| ~2027-02-22 | Wave 4 complete → Scale + Partner | **+3 нед** vs prior 2027-02-02 |

## Update protocol

При phase complete / blocker resolved / новом ADR:

1. Обновить этот STATUS.md
2. Cross-ref в commit-message: `chore(status): wave 0 phase 00.X complete`
3. Append JOURNAL.md entry для historical record
