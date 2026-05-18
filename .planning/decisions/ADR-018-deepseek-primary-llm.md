# ADR-018: DeepSeek как primary LLM-стек

- **Status:** Accepted (amendment 2026-05-19, see «Wave 0 RU-currency model»)

## Wave 0 RU-currency model (2026-05-19)

> Adopted in pre-Phase-00.3 contract extension (Phase 00.3 + 00.4 combined PR). Product launches on the RU market; customer-facing billing is **RUB**.

1. **Three-currency row in `llm_usage_log`:**
    - `cost_usd numeric(10,6)` — provider native cost (source-of-truth for provider invoice reconciliation; DeepSeek, OpenAI, Anthropic all bill USD).
    - `cost_rub numeric(12,4)` — customer-facing settlement (`cost_usd × fx_rate_usd_to_rub`).
    - `fx_rate_usd_to_rub numeric(10,6)` — FX snapshot pinned at request-time so historical rows remain consistent even when FX drifts.
2. **FX-rate source.** Wave 0: env constant `FX_RATE_USD_TO_RUB` (default `100.0`, overridable). Phase 00.6 deploy phase: Yandex Cloud config (`TBD_FX_RATE_USD_TO_RUB_OVERRIDE`). Wave 1+: live FX feed (CBR API) cached 1h.
3. **`billing.credit_transactions` (SKELETON inline).** Customer-side settlement entirely in RUB: `amount_rub` + `amount_credits` + `balance_after_credits` + audit `fx_rate_usd_to_rub`. Wave 0: `1 credit == 1 RUB` (no conversion table); Wave 2+ pricing_table introduces dynamic conversion.
4. **Atomic 3-field write contract.** `record_llm_cost(...)` writes `cost_usd`, `cost_rub`, `fx_rate_usd_to_rub` to `llm_usage_log` AND `amount_rub` + `fx_rate_usd_to_rub` to `credit_transactions` in a single transaction. Invariant: `SUM(credit_transactions.amount_rub) == SUM(llm_usage_log.cost_rub)` per cell. Verified by `test_cost_ledger_sum_match`.
5. **Provider USD pricing table.** `pricing_service.PROVIDER_PRICING_USD_PER_1K_TOKENS` keeps DeepSeek/Yandex/GigaChat USD prices per provider docs. Yandex/GigaChat invoices arrive in RUB — we record their native RUB as `cost_rub` directly and back-derive `cost_usd = cost_rub / fx_rate` (still atomic, just reversed source).
6. **BYOK soft-quota stays USD.** `byok_keys.monthly_quota_usd` matches the provider-side billing unit (DeepSeek/OpenAI bill USD). Workspace UI shows RUB-equivalent at current FX rate.



## Decision

**DeepSeek (V3 + R1) — primary premium LLM-стек с Wave 0:**
- **DeepSeek-V3** — general (Coordinator, Writer, Researcher, SMM, Manager, Sales, …)
- **DeepSeek-R1** — reasoning-heavy (Analyst, Coordinator при complex decomposition, Юрист, Accountant)

### Технические характеристики

| Параметр | DeepSeek-V3 | DeepSeek-R1 |
|---|---|---|
| Назначение | General | Reasoning |
| Input cost / 1M tokens | $0.27 | $0.55 |
| Output cost / 1M tokens | $1.10 | $2.19 |
| Context window | 128K | 128K |
| Tool-use / function calling | ✅ OpenAI-compatible | ✅ |
| Streaming | ✅ | ✅ |
| Prompt caching | ✅ (native) | ✅ |
| Multilingual (RU) | Хороший | Хороший |
| Open weights | ✅ (MIT-friendly) | ✅ |
| API endpoint | api.deepseek.com | api.deepseek.com |

### Доступ из РФ

- Прямой API (api.deepseek.com) — без VPN, без прокси
- Оплата РФ-картами / USDT / Alipay / WeChat Pay
- Нет санкций со стороны DeepSeek на РФ
- Нет TOS-ограничений на повторную перепродажу через нашу платформу

### Routing per role (Wave 0)

```python
ROLE_TO_MODEL = {
    "coordinator": "deepseek-r1",      # reasoning для decomposition
    "writer": "deepseek-v3",            # general text generation
    "researcher": "deepseek-v3",        # web-search + summarization
    "analyst": "deepseek-r1",           # reasoning + Pyodide code-gen
    "lawyer": "deepseek-r1",            # reasoning + careful disclaimers
    "accountant": "yandex-pro",         # домен 1С — yandex лучше знает РФ
    "smm": "deepseek-v3",
    "designer": "deepseek-v3",          # textual descriptions
    "manager": "deepseek-v3",
    "sales": "deepseek-v3",
}
```

В Wave 1+ user/cell может override routing через settings.

### Fallback при недоступности DeepSeek

- Primary: DeepSeek-V3 / R1
- Secondary: YandexGPT-Pro
- Tertiary: GigaChat-Pro
- Уведомление пользователя через UI + Telegram при auto-fallback

## Stack-preference per cell

Для гос-сектора / regulated отраслей: `stack_preference = "ru-only"` — принудительно использует YandexGPT/GigaChat, отключает DeepSeek.

## ФЗ-152 + cross-border consent

DeepSeek политика хранения данных: данные uploaded для inference могут логироваться на стороне DeepSeek.
- Клиент даёт consent на использование международного стека
- ПДн рекомендуем обрабатывать через ru-only режим

## Open weights возможность (Wave 5+)

DeepSeek open weights позволяют self-host в Wave 5+:
- Yandex DataSphere GPU или собственные A100/H100
- Полный data-residency (никаких внешних API)
- Альтернатива для Enterprise on-premise

## Links

- Risks: [R-01](../risks/REGISTER.md), [R-04](../risks/REGISTER.md), [R-08](../risks/REGISTER.md)
- Phase: 00.4 (DeepSeek + YandexGPT + GigaChat в gateway)
- Related ADRs: ADR-002 (LLM gateway), ADR-008 (billing pricing)
