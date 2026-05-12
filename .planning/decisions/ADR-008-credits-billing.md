# ADR-008: Team-кредиты + ЮKassa, Solo/Команды 5/15/30 + BYOK режим

- **Status:** Accepted

## Decision

### Tariff matrix

| Тариф | ₽/мес | Cells | Agents | Included T-credits | BYOK-mode |
|---|---|---|---|---|---|
| **Trial** | 0 (14 дней, без карты) | 1 | 3 | 500 (≈100 задач) | — |
| **Solo** | 990 | 1 | 3 | 300 (≈60-100 задач) | 490 |
| **Команда 5** | 1900 | 3 | 5 | 600 (≈120-200 задач) | 890 |
| **Команда 15** | 4900 | 5 | 15 | 2000 (≈400-700 задач) | 2400 |
| **Команда 30** | 9900 | 10 | 30 | 5000 (≈1000-1700 задач) | 4900 |
| **Enterprise** | Custom | Custom | Custom | Custom | + on-premise |

### Курс Team-credit

- **Wave 0-1 (только DeepSeek + RU):** единый курс **1× для всех ролей**
- **Wave 2+ при добавлении Anthropic/OpenAI через прокси:** **3× для Western стека**
- Прозрачный psychological anchor: «1 T-credit ≈ ₽10 (DeepSeek-V3 средняя задача с tool-use)»
- Курс «T-credit → токены» publish в `/api/billing/credit-rate`

### Soft / Hard caps

| Тариф | Soft-cap | Hard-cap | Overage |
|---|---|---|---|
| Trial | 400 (warning) | 500 | блок |
| Solo | 450 (notification) | 600 | +50% к курсу |
| Команда 5 | 900 | 1200 | +40% |
| Команда 15 | 3000 | 4000 | +30% |
| Команда 30 | 7500 | 10000 | +25% |

### Per-task лимиты

- Default: soft-cap 50 T-credits на задачу, hard-cap 100 T-credits
- Настраивается per cell в settings (max 200 T-credits)

### Перенос остатка

- 50% неиспользованных T-credits переносится на следующий период
- Потолок переноса: ≤ 1 месячный объём
- Auto-expire: unused переносы expire через 60 дней

### Free trial

- 14 дней + 500 T-credits, без привязки карты
- Hard-cap 500 T-credits — anti-abuse (R-25)
- 1 trial per email/IP/device
- Auto-cleanup orphaned trials через 14 дней (R-26)
- При conversion в paid — trial-cell мигрирует в полноценную cell

### BYOK mode

- Клиент подключает свой API-ключ (DeepSeek / YandexGPT / GigaChat / OpenAI / Anthropic — 9 провайдеров)
- Платит только platform-fee subscription: ₽490 / 890 / 2400 / 4900 (≈50% от managed-tariff)
- 0 T-credits included — клиент платит провайдеру напрямую через API quota
- Маркетинговое сообщение: «Свой ключ → -50% от подписки»

### Курсовая защита (managed-режим)

- Курс пересматривается каждые 6 мес
- Pricing-revision trigger при изменении USD/RUB >15% от baseline
- Уведомление за 30 дней до изменения

### Платёжный процессор

- **ЮKassa** для РФ-эмиссионных карт (Сбер, Тинькофф, ВТБ, и т.д.) + СБП
- Тинькофф Бизнес / Точка для B2B-счетов в Wave 3+
- Auto-renewal subscriptions через ЮKassa recurring API

### Stack-preference UI-prompt при cell creation

3 опции (без указания конкретных моделей кроме РФ):
- 🚀 **«Оптимальное качество»** (default): «Используется лучший доступный AI-стек для качества и скорости. Подходит для большинства задач.»
- 🇷🇺 **«Только РФ»**: «Только российские AI-провайдеры (YandexGPT, GigaChat). Для гос-сектора, банков, медицины и других regulated отраслей.»
- 🔑 **«Свой ключ» (BYOK)**: «Подключите свой API-ключ — экономия до 50% на токенах.»

### Marketing positioning per tariff

| Тариф | Целевой клиент | Headline |
|---|---|---|
| Solo | ИП, фрилансер, self-employed | «AI-помощник для ИП за ₽990» |
| Команда 5 | СМБ-команда 2-5 чел | «Полная AI-команда за ₽1900» |
| Команда 15 | Растущий СМБ 5-15 чел | «AI-департамент для растущего бизнеса» |
| Команда 30 | Зрелый СМБ 15-30 чел | «Полный AI-штат для среднего бизнеса» |
| Enterprise | Крупный B2B, гос-сектор | «Кастомное AI-решение с on-premise опцией» |
| BYOK mode | Tech-savvy / price-sensitive | «Свой ключ — наша платформа» |

## Monitoring

- Cannibalization metric: monitor managed vs BYOK split. Если >40% выбирают BYOK — пересмотр pricing
- ARPU per tariff per mode dashboard

## Links

- Risks: [R-04](../risks/REGISTER.md) (runaway costs), [R-16](../risks/REGISTER.md) (BYOK ARPU), [R-25](../risks/REGISTER.md) (trial abuse), [R-26](../risks/REGISTER.md) (trial-cell cost)
- Phase: 01.4 (Billing + ЮKassa + tariffs + BYOK)
- Related ADRs: ADR-002 (LLM gateway), ADR-018 (DeepSeek), ADR-022 (Coordinator wizard)
