# tools/ — MCP Tool Registry

Реестр инструментов (MCP-tool slugs), к которым агенты обращаются. Маппится на operationIds из `contracts/*/api.yaml`.

**ADR refs:** [ADR-013](../decisions/ADR-013-mcp-protocol.md) (MCP protocol)

## Файлы

| Файл | Содержание |
|---|---|
| [`registry.md`](./registry.md) | Полный реестр tool-slugs по bounded-context'ам с allowlist-правилами |

## Правила

- Каждый agent role (`.claude/agents/<role>/`) или vertical prompt (`verticals/<slug>/prompts/<role>.md`) объявляет свой `tools-allowlist`.
- Slug должен существовать в `registry.md` — иначе reviewer-backend блокирует PR.
- При добавлении нового MCP-сервера — обновлять `registry.md` + ADR (если меняется протокол).
