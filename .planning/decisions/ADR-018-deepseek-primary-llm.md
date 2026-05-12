# ADR-018: DeepSeek как primary LLM-стек

- **Status:** Accepted

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
