# Wave 0 — Phase Index

| Phase | Slug | Длительность | Dependencies | Owner |
|---|---|---|---|---|
| [00.1](./phases/00.1-repo-cicd.md) | repo-cicd | 3 дня | — | DevOps |
| [00.2](./phases/00.2-custom-jwt-auth.md) | custom-jwt-auth | 2 дня | 00.1, OQ-04 (РКН) | Tech Lead |
| [00.3](./phases/00.3-db-rls-multitenancy.md) | db-rls-cell | 5 дней | 00.1 | Senior Backend |
| [00.4](./phases/00.4-llm-gateway.md) | llm-gateway | 5 дней | 00.1 | Tech Lead |
| [00.2.5](./phases/00.2.5-integration.md) | integration | 1 день | 00.2 + 00.3 + 00.4 | Tech Lead |
| [00.5](./phases/00.5-pydantic-ai-productivity-team.md) | pydantic-ai-productivity-team | 5 дней | 00.2.5 | Senior Backend |
| [00.6](./phases/00.6-deploy-observability.md) | deploy-observability | 3 дня | 00.1, 00.5 | DevOps |
| [00.7](./phases/00.7-frontend-skeleton.md) | frontend-skeleton | 4 дня | 00.1, 00.2, 00.5 | Senior Frontend |
| [00.8](./phases/00.8-design-restyling.md) | design-restyling | 2–3 дня | 00.7, ADR-031 | Designer + Senior Frontend |

## Граф зависимостей

```
00.1 (repo)
 ├─→ 00.2 (custom JWT auth)
 ├─→ 00.3 (db + cell-aware RLS)  ─┐
 └─→ 00.4 (llm gateway + MCP)  ──┴─→ 00.5 (Pydantic-AI + productivity-core horizontal team)
                                       │
                                       ├─→ 00.6 (deploy + observability)  ∥ parallel
                                       └─→ 00.7 (frontend skeleton)
                                             └─→ 00.8 (design restyling)
```

> **Revision 2026-05-15:** Phase 00.5 anchor changed: WB-Селлер vertical team → horizontal `productivity-core` team (Coordinator + Researcher + Writer + Analyst). Demo-сценарий — «Market & content brief для нового продукта». WB-Селлер team-preset переезжает в Wave 2. See [ADR-017](../../decisions/ADR-017-vertical-templates.md) revision.

> **Revision 2026-06-11:** Phase 00.8 (design restyling — professional nordic v0.2) вставлена после 00.7 per founder grill-session + [ADR-031](../../decisions/ADR-031-design-direction-restyling.md). +2–3 frontend-дня; НЕ гейтит `internal_demo_passed` (D5 = founder 10× anchor run, независимый Track A).

## Параллельность

- 00.2, 00.3, 00.4 могут идти параллельно после 00.1
- 00.6 и 00.7 идут параллельно после 00.5 (per Session 4 C-D8 — ∥ placement, оба после 00.5)
- 00.7 frontend-implementer работает с backend mocks для `/api/auth/*`, `/api/cells/*`, `/api/tasks/*` пока 00.2/00.5 не Done — но контракты в `contracts/*` fix'д Wave 0

## Total

- 27 человеко-дней работы (23 backend + 4 frontend NEW per Session 4 C-D2)
- 15 рабочих дней (3 недели) с учётом 00.6 ∥ 00.7
- Команда (per Session 1 DECISION-3): solo founder + 11 persistent Opus AI-агенты (per ADR-023):
  - architect, planner, memory-curator — cross-cutting
  - designer, frontend-implementer, backend-implementer — implementation
  - reviewer-frontend, reviewer-backend, reviewer-security, verifier, evaluator — quality gates
- AI-velocity timeline пересчёт deferred к Milestone D per Session 3 Q4 (Wave 0 acceptance gate retro)

## Acceptance gate to Wave 1

- [ ] Все 9 phases (00.1–00.8, включая 00.2.5) в статусе Done
- [ ] Internal demo (productivity-core horizontal team end-to-end через UI на сценарии «Market & content brief») прошёл
- [ ] 3 артефакта demo-run-а соответствуют acceptance criteria (brief.md ≥1500w, competitive-matrix.md ≥5×4, content-plan.md 10 posts)
- [ ] End-to-end demo latency ≤120 sec p95, cost ≤30¢
- [ ] Retro проведено
- [ ] Role-prompts hardening backlog заполнен (для Phase 01.1)
- [ ] Risks register обновлён
- [ ] Wave 1 README пересмотрен

См. [gates/wave-0-to-1.md](../../gates/wave-0-to-1.md) — hard threshold `internal_demo.passed=true`.
