# ADR-013: MCP-протокол как universal connector layer + кураторский каталог

- **Status:** Accepted

> **Amendment 2026-07-11 (founder-grill D-04, Wave-2 planning):** реализация настоящего MCP-протокола (ClientSession, транспорты, community-каталог) — **Wave 3**. Wave 0–2 фактическая архитектура — native-tool callables per [ADR-041](./ADR-041-connector-architecture-native-tools.md) (Wave-0 MCP-клиент — stub). Виденье «каталог интеграций поверх MCP» сохраняется как целевое; bitrix24/amocrm-серверы — вместе с СМБ-Sales вертикалью (W3), wb-partners — удалён вместе с WB-вертикалью (D-06).
>
> **Re-revision 2026-07-11 (grill-доп, D-26, суперсид D-04):** MCP-протокол **возвращён в Wave 2 замыкающей фазой [02.13](../roadmap/wave-2-pixel-catalog/phases/02.13-mcp-protocol.md)** (место освободилось после удаления WB): реальный клиент + каталог интеграций UI + первые community-серверы **github-mcp + google-sheets-mcp**. Наши коннекторы остаются native (ADR-041 не отменяется — MCP = второй путь для чужих серверов). Остальной community-набор + user-supplied серверы — W3. 02.13 — первый кандидат на перенос при затягивании волны (D-27).

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
| **Wave 0** | MCP infrastructure (client + auth + Lockbox); built-in web_search + read_url |
| **Wave 1** | + Telegram-mcp **v0.2 (Read + post + Business API per [ADR-030](./ADR-030-telegram-business-api.md))**, Yandex-Disk-mcp, IMAP-SMTP-mcp (наши) |
| **Wave 2** | + WB-Партнёры-mcp (graduated из W0 plan), Bitrix24-mcp, amoCRM-mcp (наши) + GitHub-mcp, Notion-mcp, Slack-mcp (community-based) + **Telegram Mini App контейнер** |
| **Wave 3** | + Ozon-Seller-mcp (для ИП-Бух / СМБ-Sales verticals — see [ADR-017](./ADR-017-vertical-templates.md) re-ordering), 1C-REST-mcp, Эльба-mcp, Контур-Экстерн-mcp, Тинькофф-Бизнес-mcp; расширение community-catalog до 20+ |
| **Wave 4** | + Custom MCP server addition UI; community marketplace draft; Telegram Stars billing (parallel к ЮKassa per [ADR-030](./ADR-030-telegram-business-api.md)) |
| **Wave 5+** | + Open marketplace MCP-серверов с UGC |

## Maintenance

- Forking + maintaining наших копий critical community MCP-servers (GitHub, Notion, Slack)
- Version pinning per MCP-protocol release
- Health-check MCP-servers каждые 60 сек

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-18](../risks/REGISTER.md)
- Phase: 00.4 (MCP infrastructure), 01.10 (3 первых MCP — telegram-mcp v0.2 включает Business API), 02.x (vertical MCP + Mini App), 03.x (расширение)
- Related ADRs: ADR-003 (Pydantic-AI), ADR-014 (capability sandboxing), ADR-017 (vertical-templates используют MCP), [ADR-030](./ADR-030-telegram-business-api.md) (Telegram Business API integration detail)
