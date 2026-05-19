# contracts/ — Bounded Context Contracts

API + data contracts по bounded-context'ам (DDD). Каждый поддомен содержит OpenAPI / события / SQL schema.

**ADR refs:** [ADR-024](../decisions/ADR-024-bounded-context-contracts.md), [ADR-009](../decisions/ADR-009-multitenancy-3-levels.md)

## Naming bridge (2026-05-19): `organization` → `workspace`

The legacy term `organization` (and column `organization_id`) was renamed
to `workspace` (`workspace_id`) across all authoritative DDL / API / events
per ADR-024 amendment 2026-05-19. Where you still encounter the legacy term
in narrative documentation (e.g. `artifacts/README.md`, `memory/README.md`,
`billing/events.yaml` description strings), treat it as a synonym of the
canonical `workspace`. New contract content MUST use `workspace`.

## Bounded contexts (Wave 0 critical)

| Поддомен | Содержание |
|---|---|
| [`agents/`](./agents/) | Agent archetypes, prompt versioning, runtime API |
| [`artifacts/`](./artifacts/) | Артефакты (Yjs docs + S3 ассеты) |
| [`billing/`](./billing/) | T-credits, тарифы, ЮKassa |
| [`iam/`](./iam/) | Identity, authentication, encryption / KMS |
| [`llm-gateway/`](./llm-gateway/) | Multi-provider LLM proxy + BYOK |
| [`mcp/`](./mcp/) | MCP-протокол для connectors |
| [`memory/`](./memory/) | Agent memory (cell + role, PARA) |
| [`multitenancy/`](./multitenancy/) | Cell-first multitenancy, RLS |
| [`rbac/`](./rbac/) | Roles, permissions, scope |
| [`tasks/`](./tasks/) | Task lifecycle + CloudEvents |

## Когда читать

- При планировании phase, затрагивающей конкретный контекст — читать его `README.md`.
- При изменении API / схемы — обновлять схема + bump семвера в самом контракте.
