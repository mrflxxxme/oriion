# 06 — Billing Model

## Краткое summary

- **3 платных тарифа + Enterprise:** $29 / $89 / $179 / Custom
- **Free / No Plan:** 0 teams, exploration-only
- **Внутренняя валюта:** Teamly Dollars (T$), курс **1 T$ = $1.00** (нет курсового спрэда)
- **Payment processor:** Polar.sh (US/EU SaaS-friendly)
- **BYOK:** до **−80%** для клиентов с собственным Anthropic/OpenAI key
- **Сверхпотребление:** "Top up Teamly Dollars anytime" (overage = pay-per-use на top of plan)

## Tariff matrix

| Параметр | Teamly 5 | Teamly 15 (★ Most Popular) | Teamly 30 | Enterprise |
|---|---|---|---|---|
| Monthly price (USD) | $29 | $89 | $179 | Custom |
| AI Employees (agents) | 5 | 15 | 30 | Unlimited |
| Workspaces | 3 | 5 | 10 | Custom |
| AI Teams (Cells) | 3 | 5 | 10 | Custom |
| Included Teamly $/mo | $20 | $80 | $170 | Custom |
| Cost-per-agent slot | $5.80 | $5.93 | $5.97 | — |
| Cost-per-Teamly$ included | $1.45 | $1.11 | $1.05 | — |

**Effective platform fee (без BYOK):** Tarif price − Teamly Dollars included ≈ platform margin = $9 / $9 / $9 для всех трёх tarifов. Это очень любопытно — fixed margin $9/mo вне зависимости от scale.

**С BYOK** клиент экономит "up to 80%" на usage, то есть включённые $20/80/170 Teamly Dollars пропадают (он использует свой ключ), но платит только monthly subscription = $29 / $89 / $179 → fixed cost per agent.

## Unit-economics (гипотеза)

`1 Teamly Dollar = $1.00` — это **direct passthrough** Anthropic/OpenAI API cost + наценка платформы. Сколько именно наценка — нераскрыто, но `BYOK -80%` подсказывает, что платформа берёт ~5× от raw cost (без BYOK), либо берёт $0.20 за $1.00 worth of compute с BYOK.

Это разумно: heavy Claude Sonnet calls с tool-use могут обходиться в $0.10-1.00 per task → клиент тратит $20-170 T$/мес → $4-34 raw API cost при 5× наценке.

## Free / No Plan

- 0 workspaces, 0 teams (paywall на Hire)
- Доступны: Settings, Catalog browsing, Coordinator wizard, BYOK setup
- Coordinator wizard работает (но это structured wizard, не LLM)
- Можно загрузить ключи (но они без cell неиспользуются)

## Polar.sh integration

UI-текст: «manage payment details securely in Polar»

Polar.sh — это modern payment platform with:
- Subscription management
- Usage-based billing
- Webhook events (за подпиской, top-up, cancellation)
- Strong API + developer experience
- Founder-friendly (open-source aware)

В отличие от Stripe — Polar легче onboardится для SaaS-startups, особенно open-source.

## Payment method storage

«NO BILLING ACCOUNT YET» сообщение указывает: подписка создаёт billing account в Polar для текущего user. Карта/банк → Polar, не teamly.to. Teamly хранит только Polar customer_id + plan reference.

## BYOK (Bring Your Own Key)

**Marketing claim:** "SAVE 80% ON CREDITS"

**Mechanism:**
- Клиент connects свой Anthropic/OpenAI/Google/etc. API key через `/settings/api-keys`
- Когда agent делает inference — backend использует клиентский ключ, не Teamly's
- Стоимость = клиентская подписка Anthropic billed напрямую к ним
- Teamly platform fee: «small» (10-20% guess), не markup on tokens
- Не работает для Sonnet/Opus included Teamly Dollars — там Teamly's keys

**Supported providers для BYOK (9 шт.):**
1. anthropic (Claude)
2. openai (GPT)
3. google (Gemini)
4. openrouter
5. minimax (Chinese)
6. zai (GLM)
7. brave (search)
8. exa (search)
9. composio (integrations)

## Sumo/Top-up

«Top up Teamly Dollars anytime» — клиент может купить additional T$ сверх monthly включённых. Цена тоже не раскрыта, гипотеза: $1 за $1 T$.

## Currency / Tax

- USD only. Нет EUR/GBP/RUB.
- Tax обработка — на стороне Polar (handles VAT/sales tax for EU/US/etc.).
- Очень неудобно для РФ-клиентов: нет ЮKassa, СБП, рублёвых счетов.

## Pricing psychology

«1 credit = $1.00» — psychologically straightforward.
$29 / $89 / $179 — все на «$X9» pattern (charm pricing).
«Most Popular» badge на $89 plan — anchor pricing.
Per-agent cost ~$6/agent across all plans — Teamly hides this; if they showed «$5.97/agent/mo for 30 agents», it would be a tougher sell.

## Visible billing UI elements

- "BILLING" header (Settings → Billing-like context)
- "CREDITS TRACKED" badge (green pill)
- "CHOOSE YOUR PLAN" headline
- "Launch dedicated AI teams in the cloud without your own infrastructure. Each workspace runs its own AI team, and Teamly Dollars pay for real agent work across Sonnet and Opus."
- 4 tariff cards
- Footer: «Every plan includes dedicated infrastructure. Teamly Dollars are used by your agents as they work across Sonnet and Opus. If your team needs more capacity, you can add more Teamly Dollars anytime.»
- Stats trio: CREDITS USED / BUDGET SPENT / CREDITS REMAINING
- PAYMENT METHOD section (Polar callout)
- BYOK promo banner (gold/orange — Save 80%)

## Lifecycle hypothesis

| Event | What happens |
|---|---|
| User signs up | Creates Clerk account + Free / No Plan workspace + Coordinator (preview) |
| User clicks "Hire" on team | Toast: «Team limit reached (0/0)». Redirect to `?view=billing` |
| User upgrades | Polar checkout → on success: Webhook to teamly backend → spawn first cell + grant T$ → redirect to `/teams/new` |
| Monthly cycle | Polar charges → backend resets T$ included pool |
| BYOK setup | User adds API key in `/settings/api-keys` → backend masked + encrypted + stored |
| Cancellation | Polar webhook → backend freezes cell (read-only?) or terminates after grace period |

## Refund / cancellation policy

Не открывали Terms — статичный текст. Гипотеза based on Polar: monthly subscription, cancel anytime, no refunds (стандартный SaaS).

## Reconstruction notes (для нашего планирования)

См. `RECONSTRUCTION-NOTES.md`. Кратко:

- Наш ADR-008 (Team-кредиты + ЮKassa) сильно отличается:
  - Мы используем РФ-валюту (₽), не доллары.
  - Наш курс RU vs International stack — двухставочный (1× / 3×), у них single rate.
  - Перенос 50% остатка — у нас есть, у них нет (явно).
  - Наши soft/hard-cap — у них «top up anytime» (нет hard-cap).
  - Trial 14 дней — у них нет visible trial (free tier — exploration only, не workflow).

- **Наша курсовая защита (ADR-008 курсовая оговорка) — критично важна.** У teamly нет этой проблемы (USD-only), нам нужна явная политика на скачки RUB.

- **BYOK** — they're already on it. Нам стоит рассмотреть BYOK для Wave 3 (вместо Wave 4) для крупных клиентов. Это хороший wedge для enterprise.

- **Polar.sh** — нам недоступен (РФ), используем ЮKassa.

- **Платформа margin $9/mo fixed** — это интересная модель, упрощает unit-эконом. Подумать для нашей.
