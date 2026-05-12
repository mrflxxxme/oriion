# ADR-013: MCP-протокол как universal connector layer + кураторский каталог

- **Status:** Accepted

## Decision

**MCP (Model Context Protocol)** как universal connector layer с Wave 0. Кураторский каталог поверх MCP — для GUI-юзера выглядит как «список интеграций», под капотом — каждая = MCP-сервер.

## Architecture

```
Cell (workspace)
  └── Agent (Pydantic-AI runtime)
      └── MCP client (Pydantic-AI's native support)
          ├── Built-in tools (web_search, read_url)
          ├── РФ-killer MCP-серверы (наши, Python)
          │   ├── telegram-mcp
          │   ├── yandex-disk-mcp
          │   ├── bitrix24-mcp
          │   ├── amocrm-mcp
          │   ├── wb-partners-mcp
          │   ├── ozon-seller-mcp
          │   ├── 1c-rest-mcp
          │   ├── kontur-elba-mcp
          │   ├── kontur-extern-mcp
          │   └── tinkoff-business-mcp
          └── Community MCP-серверы (open-source, optional connect)
              ├── github-mcp
              ├── notion-mcp
              ├── linear-mcp
              ├── slack-mcp
              ├── gmail-mcp
              ├── google-drive-mcp
              └── ...
```

## Кураторский каталог UX

`/settings/integrations` UI:
- **РФ-вертикальные** (наши, brand-stamped): Telegram, Yandex.Disk, Bitrix24, amoCRM, WB Партнёры, Ozon Seller, 1С, Эльба, Контур.Экстерн, Тинькофф Бизнес
- **Глобальные** (через community MCP с нашей integration-shim): GitHub, Notion, Linear, Slack, Gmail, Google Drive, Google Sheets
- **Power-user:** «Add custom MCP server» — указать endpoint + credentials, добавляется в cell

Каждая интеграция: иконка + название + описание + кнопка [Connect]. Под капотом — поднимаем MCP-сервер связь и сохраняем credentials в Lockbox.

## Naming convention

- **Наши MCP-серверы:** `teamly-ru/<integration>-mcp` (Python пакет в `backend/src/mcp/servers/`)
- **Community:** запускаются как separate processes / Docker контейнеры, проксируются через наш MCP-orchestrator

## MCP transport

- Pydantic-AI поддерживает MCP через `mcp-python` SDK
- Transport: HTTP+SSE (remote MCP-серверы) и stdio (local Python servers)
- Authentication: per workspace credentials в Lockbox, MCP-server получает auth-token при start

## Security

- DLP-сканер на input/output каждого MCP-tool-call
- Capability sandboxing: dangerous tools require human approval (ADR-014)
- Audit log: все MCP-вызовы записаны с cell_id, agent_id, tool, args, result
- Sandbox-isolation: MCP-server процесс не имеет direct DB-access, только через scoped API tokens

## Реализация по волнам

| Волна | MCP-серверы |
|---|---|
| **Wave 0** | MCP infrastructure (client + auth + Lockbox); built-in web_search |
| **Wave 1** | + Telegram-mcp, Yandex-Disk-mcp, IMAP-SMTP-mcp (наши) |
| **Wave 2** | + Bitrix24-mcp, amoCRM-mcp, WB-Партнёры-mcp, Ozon-Seller-mcp (наши, для 5 vertical-templates) + GitHub-mcp, Notion-mcp, Slack-mcp (community-based) |
| **Wave 3** | + 1C-REST-mcp, Эльба-mcp, Контур-Экстерн-mcp, Тинькофф-Бизнес-mcp; расширение community-catalog до 20+ |
| **Wave 4** | + Custom MCP server addition UI; community marketplace draft |
| **Wave 5+** | + Open marketplace MCP-серверов с UGC |

## Maintenance

- Forking + maintaining наших копий critical community MCP-servers (GitHub, Notion, Slack)
- Version pinning per MCP-protocol release
- Health-check MCP-servers каждые 60 сек

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-18](../risks/REGISTER.md)
- Phase: 00.4 (MCP infrastructure), 01.x (3 первых MCP), 02.x (vertical MCP), 03.x (расширение)
- Related ADRs: ADR-003 (Pydantic-AI), ADR-014 (capability sandboxing), ADR-017 (vertical-templates используют MCP)
