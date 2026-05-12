# 00 — Overview: что такое teamly.to

## Краткое описание (для AI-агентов)

**teamly.to** — глобальный SaaS-сервис «managed-hosting для AI-агентов» с метафорой «AI-офис». Пользователь выбирает готовый пресет «команды», нанимает её одним кликом, ставит задачу через **Координатора** (центральный агент-роутер) и наблюдает за пиксельными агентами, выполняющими работу. Целевой клиент: solo-founder / небольшая команда / SMB, нуждающаяся в продуктивности без найма людей.

## Tagline / маркетинг

- Headline: **"Your AI Agents, Managed in the Cloud"**
- Sub: **"Managed hosting for AI agents. Zero infrastructure. Full control. Watch your AI team work in real-time through the Pixel Department."**
- Value-stack:
  - "Build your AI department at 10x less than traditional cost"
  - "$5/agent vs $50/hr"
  - "Real agents, real tasks, real results"
  - "Hire AI specialists" (фрейминг как найм сотрудников)

## Позиционирование (3 ключевые позиции)

1. **Не chatbot, а команда специалистов:** «Teamly is not another chatbot. Pick a workflow team with specialist agents, shared context, tool access, and a concrete output.»
2. **Dedicated infrastructure** per team (не shared multi-tenant): каждая команда = «cell» с явным регионом deployment.
3. **Visual AI-office** — наблюдай за командой в реальном времени.

## ЦА и use-cases

Заявленные сегменты (через team-templates):
- Marketing/SMM agencies → Marketing Team, Content Marketing Team
- E-commerce / DTC → Sales Team, Lead Research
- Dev shops / startup CTO → Dev Team, Research Team
- Solo creators / writers → Content Writer, Book Writing (Oscar Case)
- HR / People Ops → HR Team
- Wellness / lifestyle / personal productivity → Health & Wellness, Personal Effectiveness
- "Autonomous Agent" — persistent self-running agent для power-users

## Pricing snapshot (с сайта)

| План | $/мес | AI employees | Workspaces (Cells) | AI Teams | Teamly $ /мес |
|---|---|---|---|---|---|
| Free / No Plan | 0 | 0 (preview) | 0 | 0 | 0 |
| Teamly 5 | $29 | 5 | 3 | 3 | $20 |
| Teamly 15 (most popular) | $89 | 15 | 5 | 5 | $80 |
| Teamly 30 | $179 | 30 | 10 | 10 | $170 |
| Enterprise | Custom | Unlimited | Custom | Custom | Custom |

**Курс:** `1 Teamly Dollar = $1.00`. Не вторая валюта, а кредитная единица потребления токенов.

**BYOK:** до **-80%** на стоимость, если клиент подключает свой Anthropic / OpenAI ключ (платит только platform fee).

## Юнит «AI employee»

- "AI employee" = 1 агент = 1 место в плане.
- Один agent состоит из персонажа (sprite + имя, например "Mika" / "Marcus" / "Scout") + роль (Content Strategist, Copywriter, и т.д.) + tools + контекст команды.
- "Coordinator" — отдельный системный агент, всегда есть в Cell, не считается среди оплачиваемых.

## Юр.форма платежей

- Payment processor: **Polar.sh** (текст оферты упоминает «manage payment details securely in Polar»).
- Currency: USD (доллары США).
- Регион выставления: подразумевается US (нет адаптации под РФ).

## Что НЕ предлагается (или не видно)

- Маркетинга для индивидуальных потребителей (продукт явно B2B/SMB-focused).
- Российской локализации (Chrome auto-translate подменяет UI).
- ФЗ-152-compliance (хранение ПДн в РФ, согласия) — нет.
- Российских платёжных систем (ЮKassa, СБП).
- Поддержки русскоязычных LLM (GigaChat / YandexGPT) — только Sonnet/Opus/GPT/Gemini/MiniMax/Z.AI/OpenRouter.

## Source / links

- Homepage: `https://teamly.to/`
- Pricing / How it works (anchor sections same page).
- Privacy / Terms / Cookies / Licenses footer pages (не углублялись — статичные).
- Auth: Clerk (clerk.teamly.to).
- Cell deployment region (observed): `iad — Ashburn, Virginia` (AWS US-East).

См. также: `01-user-journeys.md`, `02-architecture-frontend.md`, `06-billing-model.md`.
