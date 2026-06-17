# ADR-035: DeepSeek-gated native `web_search` tool-call (Researcher)

- **Status:** Accepted (Phase 01.1 retro, AC-W1-19)
- **Date:** 2026-06-17
- **Deciders:** Tech Lead, Founder

## Context

AC-W1-19 closes the last leg of the «реальный LLM-Координатор» работы: дать
Researcher'у решать **самому**, когда и что искать в вебе, через native
function-calling — вместо Wave-0 скриптового пред-фетча (`runtime → mcp.tools.web_search`,
ADR-024 §3 Exception #3), который вызывал `web_search` детерминированно ПЕРЕД
LLM и инжектил сниппеты в sub-prompt.

Силы и constraint'ы:

- **Провайдер-несовместимость (та же, что в [ADR-032](./ADR-032-coordinator-plan-then-execute.md)).**
  Только DeepSeek форвардит OpenAI-shaped `tools` и парсит `tool_calls`
  (`providers/deepseek.py::_body`). YandexGPT и GigaChat молча игнорируют `tools` —
  native tool-loop, ушедший на них при failover, **зависнет** (модель никогда не
  получит результат инструмента, цикл не завершится корректно).
- **Failover должен оставаться робастным** ([ADR-002](./ADR-002-llm-gateway.md)):
  падение DeepSeek (402/429/5xx) не должно ронять задачу.
- **Rate-limit:** агентский цикл может звать `web_search` многократно — нужен
  Redis `ToolRateLimiter` (30/min на agent_id, Phase 00.4 §Task 14), а не один
  вызов на прогон, как у скриптового пути.

## Decision

**Native `web_search` tool-call включается ТОЛЬКО на DeepSeek; на failover
(YandexGPT/GigaChat) откатываемся к скриптовому пред-фетчу `fetch_research_context`.**
Гейт двухуровневый:

1. **Gateway-уровень (`LLMGatewayModel.request` → `router.acomplete`).**
   `function_tools` транслируются в OpenAI `tools` и форвардятся, но `acomplete`
   отдаёт `tools` провайдеру **только если** `provider_forwards_tools(slug)`
   (DeepSeek). При failover `tools` обнуляются → запрос проходит как обычный
   текст. Ответные `tool_calls` парсятся в `ToolCallPart`, `ToolReturnPart`/
   `RetryPromptPart` перекладываются обратно в `role="tool"` сообщения — полный
   tool-loop живёт в адаптере, не в провайдере.
2. **Leaf-уровень (`runtime.dispatch`).** `LLMRouter.would_use_native_tools("researcher")`
   предсказывает активного провайдера; если это DeepSeek — Researcher-агент
   строится **с** native `web_search` (rate-limited `WebSearchTool`), пред-фетч
   НЕ запускается. Иначе — старый скриптовый пред-фетч + агент без инструментов.

Так прямое ребро `runtime → mcp.tools.web_search` **снято для DeepSeek**, но
**сохранено как failover**.

## Consequences

- ✅ Researcher на DeepSeek сам решает когда/что искать (AC-W1-19); поиск
  rate-limited через Redis на native-пути.
- ✅ Failover-цепочка не ломается: на Yandex/GigaChat `tools` дропаются, задача
  завершается текстом; web-данные всё равно приходят (скриптовый пред-фетч).
- ✅ `LLMRequest.tools` / `LLMResponse.tool_calls` уже round-trip'или в
  `providers/base.py` — расширять схему не пришлось; добавился только парсинг
  `tool_calls`↔`ToolCallPart` в gateway-адаптере.
- ⚠️ Trade-off: при гонке (DeepSeek-circuit открывается между leaf-проверкой и
  вызовом) Researcher объявит инструмент, но failover на Yandex его дропнет —
  модель ответит из памяти без web-данных (редко; деградация, не отказ).
- 🔮 Future: read_url как второй native-инструмент (AC-W1-18) и BYOK-провайдеры,
  умеющие function-calling (OpenAI), можно добавить в `_NATIVE_TOOL_PROVIDERS`.

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| Native tools на всех 3 провайдерах | единый путь | Yandex/GigaChat виснут на tool-loop | ломает failover (та же причина, что в ADR-032) |
| Только скриптовый пред-фетч (Wave-0) | робастно, кросс-провайдер | Researcher не решает сам — AC-W1-19 не закрыт | не закрывает acceptance |
| Гейт по env-флагу, а не по активному провайдеру | проще | не реагирует на runtime-failover circuit'ов | гонка/зависание при падении DeepSeek |

## Links

- Phase: [01.1-retro](../roadmap/wave-1-core-mvp/phases/01.1-retro.md) — AC-W1-19
- Related ADRs: [ADR-032](./ADR-032-coordinator-plan-then-execute.md) (почему DeepSeek-only),
  [ADR-002](./ADR-002-llm-gateway.md) (gateway + failover),
  [ADR-018](./ADR-018-deepseek-primary-llm.md) (DeepSeek primary),
  [ADR-024](./ADR-024-bounded-context-contracts.md) (§3 Exception #3 — снятое прямое ребро)
