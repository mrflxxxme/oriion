# ADR-002: LLM Multi-provider Gateway — триконтурный стек с BYOK first-class

- **Status:** Accepted

## Decision

**Триконтурный LLM-стек:**

### Контур 1: China (Premium, прямой API из РФ) — Wave 0+
- **DeepSeek-V3** — general (Coordinator, Writer, Researcher, SMM, …)
- **DeepSeek-R1** — reasoning-heavy (Analyst, Coordinator при complex decomposition, юр-задачи)
- Эндпойнт: `api.deepseek.com` (прямой, без прокси)
- Оплата: РФ-картой / USDT / Alipay

### Контур 2: RU (Managed + Business, прямой API) — Wave 0+
- **YandexGPT 5 Pro** — managed alternative, embedding
- **YandexGPT 5 Lite** — cost-efficient для простых задач (filter-agent, classification)
- **GigaChat Pro / Max** — Sberbank
- Embedding: **YandexGPT Embeddings** (text-search-doc / text-search-query)

### Контур 3: Western (Wave 2+, через прокси)
- **Anthropic Claude Sonnet 4 / Opus**
- **OpenAI GPT-4o / o1**
- Через **прокси-посредников** (multi-proxy + собственный VPS)
- Только через BYOK preferred

### BYOK first-class с дня 1
- 9 провайдеров поддерживается в API Keys UI: `deepseek`, `yandex`, `gigachat`, `openai`, `anthropic`, `google`, `openrouter`, `brave`, `exa`
- Платформа берёт fixed platform-fee, не markup на токенах

## Architecture

`backend/src/llm_gateway/` модуль:

```
llm_gateway/
├── providers/
│   ├── deepseek.py      # api.deepseek.com (OpenAI-compatible SDK)
│   ├── yandex.py        # yandex-cloud-ml-sdk
│   ├── gigachat.py      # gigachat-py
│   ├── anthropic.py     # anthropic SDK (Wave 2+ через base_url override для прокси)
│   ├── openai.py        # openai SDK (Wave 2+)
│   ├── google.py        # Wave 3+
│   ├── openrouter.py    # openai-compatible Wave 3+
│   └── base.py          # LLMProvider Protocol
├── router.py            # роутинг per role + per cell config
├── billing.py           # учёт токенов в credit_transactions
├── proxy_pool.py        # multi-proxy для Western контура (Wave 2+)
├── byok.py              # BYOK key management (Lockbox + masked UI)
├── pricing.py           # прайс-таблицы per provider per model
└── health.py            # health-check каждые 30 сек, status per provider
```

## Routing logic

```python
def choose_provider(role: Role, cell: Cell, task: Task) -> Provider:
    # 1. Если cell.preferences.byok[provider].enabled — клиентский key
    # 2. Иначе managed по приоритету role.recommended_model_tier:
    #    coordinator → deepseek-r1 (reasoning) | deepseek-v3 (default)
    #    researcher → deepseek-v3 | yandex-pro (если cell.stack == "ru-only")
    #    writer → deepseek-v3 | yandex-pro
    #    analyst → deepseek-r1 | yandex-pro
    #    lawyer → deepseek-r1 + approval_required
    #    accountant → yandex-pro + approval_required
    # 3. Cell.stack_preference: 'default' / 'ru-only' / 'byok-only' / 'premium-western'
    # 4. Failover: при недоступности primary — fallback по health-check
```

## Two-rate курс

- **Wave 0-1:** единый курс **1× для всех ролей** (только DeepSeek + RU)
- **Wave 2+ при добавлении Anthropic/OpenAI:** **3× для Western стека**

## Hot-swap провайдеров

- Конфиг `LLM_PROVIDERS` в БД-таблице `system_config` per environment
- In-memory cache с invalidation через Postgres NOTIFY/LISTEN
- Admin-endpoint `POST /api/admin/llm/reload-config`

## Health check + failover

- Periodic ping каждые 30 сек per provider
- Метрики в Grafana: `llm_provider_availability`, `llm_provider_latency_ms`
- Public status page (status.<brand>.ru)
- При недоступности primary >5 минут: user opt-in policy (`wait` / `fallback_ru` / `cancel`) + notification в UI + Telegram

## Prompt caching

- DeepSeek: native prompt-caching (V3/R1)
- Anthropic (Wave 2+): `cache_control: ephemeral` на system prompts
- YandexGPT / GigaChat: when API support появится

## Pricing (актуальные на 2026-05)

| Provider | Model | Input $/1M | Output $/1M | Контекст |
|---|---|---|---|---|
| DeepSeek | V3 | $0.27 | $1.10 | 128K |
| DeepSeek | R1 | $0.55 | $2.19 | 128K |
| YandexGPT | 5 Pro | ~$0.50 (₽) | ~$1.50 | 32K |
| YandexGPT | 5 Lite | ~$0.20 | ~$0.30 | 32K |
| GigaChat | Pro | ~$0.40 | ~$1.00 | 32K |
| Anthropic (W2+) | Sonnet 4 | $3.00 (+прокси ~30%) | $15.00 | 200K |
| OpenAI (W2+) | GPT-4o | $2.50 (+наценка) | $10.00 | 128K |

## Links

- Risks: [R-01](../risks/REGISTER.md) (отказ провайдера), [R-04](../risks/REGISTER.md) (курс), [R-08](../risks/REGISTER.md) (регуляторика), [R-16](../risks/REGISTER.md) (BYOK ARPU), [R-17](../risks/REGISTER.md)
- Phase: 00.4 (gateway initial), 01.x (BYOK расширение), 02.x (Western стек)
- Stack: [_meta/stack.md](../_meta/stack.md)
- Related ADRs: ADR-008 (billing), ADR-018 (DeepSeek)
