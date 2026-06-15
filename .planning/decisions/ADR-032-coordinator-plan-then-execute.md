# ADR-032: Coordinator decomposition — plan-then-execute via PromptedOutput (не native tool-calling)

- **Status:** Accepted (Phase 01.1 Track A, 2026-06-15)

## Decision

Реальный LLM-Координатор (AC-W1-16b / AC-W1-24) решает декомпозицию по схеме
**plan-then-execute через Pydantic-AI `PromptedOutput`**, а НЕ через native
tool-call loop, как формулировал acceptance AC-W1-16 («Coordinator decides
decomposition via an LLM tool-call»). Это сознательное отклонение от формулировки
AC (фиксируется здесь, не «тихо»).

- Координатор за **один** вызов возвращает весь `CoordinatorOutput.delegation_plan`
  как JSON. PromptedOutput: JSON-схема инжектится в system-message
  (`LLMGatewayModel.request` → `prepare_request` → `prompted_output_instructions`),
  ответ парсится из текста — никакого function-calling.
- `runtime.dispatch.PlanExecutingCoordinator` исполняет план: для каждого шага
  вызывает leaf-runner с `goal` как sub-prompt, повторно применяя guard'ы
  (`assert_delegation_allowed`: in-team slug + depth), и материализует артефакт
  типа `DelegationStep.artifact_type` (тип приходит из плана, не из code-side map).

## Почему отклонён native tool-calling

1. **Провайдер-несовместимость.** Координатор (ADR-018) — DeepSeek; `deepseek-reasoner`
   (R1) не поддерживает ни function-calling, ни JSON-output. `deepseek-chat`
   умеет — но см. п.2.
2. **Failover ломается.** Только DeepSeek (+ BYOK) форвардит `tools` / парсит
   `tool_calls`; YandexGPT и GigaChat — нет. Native tool-loop при failover на
   Yandex/GigaChat молча обрывается. PromptedOutput (plain text in/out) робастен на
   всех 3 провайдерах и сохраняет failover-цепочку ([ADR-002](./ADR-002-llm-gateway.md)).
3. **Меньше surface.** Не нужна трансляция ToolCallPart/ToolReturnPart в gateway
   (это отдельный пин AC-W1-19 для leaf web_search, отложен).

## Consequences

- Координатор больше НЕ носит `delegate_task` как tool (`tools=[]`); тот же
  guard-хелпер переиспользуется при исполнении плана — типизированные guard'ы
  сохранены, не потеряны.
- `_SUB_PROMPT_FRAMING` / `DEFAULT_PIPELINE` / `_ARTIFACT_KIND` / `ScriptedCoordinator`
  удалены — произвольные промпты работают (AC-W1-24); market-brief framing живёт
  только как frontend-пресет.
- **AC-W1-16 закрыт ЧАСТИЧНО:** 16b (реальный Координатор) ✅ по этой схеме; 16a
  (Dramatiq 202<1s) + AC-W1-1 (Redis-SSE) отложены в infra-PR — dispatch остаётся
  inline-sync.
- Риск: дисциплина fenced-JSON у `deepseek-chat` под нагрузкой — проверяется live
  golden-прогоном; при сбоях — extract-first-`{...}` ретрай (добавить по факту).
- Native tool-calling возвращается точечно для leaf web_search (AC-W1-19), не для
  Координатора.

## Validated live (2026-06-15, локальный `oriion_live` стек)

Прогон на живом стеке (DeepSeek **402** out-of-balance + YandexGPT **401** expired-IAM → failover на GigaChat):

- ✅ **PromptedOutput на реальном провайдере:** GigaChat вернул schema-conformant JSON → распарсился в `CoordinatorOutput`. Центральный риск (fenced-JSON discipline на реальном LLM) — снят на GigaChat.
- ✅ **Генерализация (AC-W1-24):** разные промпты → разные планы: тривиальный + «сравни 3 CRM» → **direct-action** (пустой план, ответ в `summary`); «перепиши лендинг» → **writer-only** план с `artifact_type="copywriting"` (НЕ `brief` — тип из плана, не из slug).
- ✅ **Multi-system fallback подтверждён live:** двух-system-message запрос Координатора (PromptedOutput) GigaChat отверг **422**; после merge в один system-message — **200**. Зафиксировано в `_messages_to_openai_shape` + unit-тест (fix-commit).
- ⚠️ **Market-brief AC8/9/10 НЕ подтверждён:** GigaChat ReadTimeout'ит на ≥1500-словном writer (30s per-call provider timeout) и не уложится в AC8 latency. Закрытие требует **funded DeepSeek** (быстрый primary) — founder billing action.

## Links

- [ADR-002](./ADR-002-llm-gateway.md) — LLM gateway + failover (почему plain-text важен)
- [ADR-018](./ADR-018-deepseek-primary-llm.md) — DeepSeek primary (reasoner vs chat)
- [ADR-016](./ADR-016-team-first-ux.md) — team-first (leaf не делегируют)
- [ADR-024](./ADR-024-bounded-context-contracts.md) — agents «что делегировать» / runtime «как исполнять»
- Phase-spec: `../roadmap/wave-1-core-mvp/phases/01.1-retro.md` AC-W1-16/24
