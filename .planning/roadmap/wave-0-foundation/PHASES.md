# Wave 0 — Phase Index

| Phase | Slug | Длительность | Dependencies | Owner |
|---|---|---|---|---|
| [00.1](./phases/00.1-repo-cicd.md) | repo-cicd | 3 дня | — | DevOps |
| [00.2](./phases/00.2-custom-jwt-auth.md) | custom-jwt-auth | 2 дня | 00.1, OQ-04 (РКН) | Tech Lead |
| [00.3](./phases/00.3-db-rls-multitenancy.md) | db-rls-cell | 5 дней | 00.1 | Senior Backend |
| [00.4](./phases/00.4-llm-gateway.md) | llm-gateway | 5 дней | 00.1 | Tech Lead |
| [00.5](./phases/00.5-pydantic-ai-wb-team.md) | pydantic-ai-wb-team | 5 дней | 00.3, 00.4 | Senior Backend |
| [00.6](./phases/00.6-deploy-observability.md) | deploy-observability | 3 дня | 00.1, 00.5 | DevOps |

## Граф зависимостей

```
00.1 (repo)
 ├─→ 00.2 (custom JWT auth)
 ├─→ 00.3 (db + cell-aware RLS)  ─┐
 └─→ 00.4 (llm gateway + MCP)  ──┴─→ 00.5 (Pydantic-AI + WB team) ──→ 00.6 (deploy + obs)
```

## Параллельность

- 00.2, 00.3, 00.4 могут идти параллельно после 00.1
- 00.6 — после 00.5

## Total

- 23 человеко-дня работы
- 15 рабочих дней (3 недели)
- Команда: 2 × full + 0.5 DevOps = 2.5 FTE × 15 = 37 человеко-дней capacity
- Запас ~38% на ревью, AI-cost, отладку

## Acceptance gate to Wave 1

- [ ] Все 6 phases в статусе Done
- [ ] Internal demo (WB-Селлер team) прошёл
- [ ] Retro проведено
- [ ] Risks register обновлён
- [ ] Wave 1 README пересмотрен
