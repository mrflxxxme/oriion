# 08 — Marketing Content & Positioning

## Headline & sub-headlines

- **H1 (landing):** «Your AI Agents, Managed in the Cloud»
- **Sub:** «Managed hosting for AI agents. Zero infrastructure. Full control. Watch your AI team work in real-time through the Pixel Department.»

- **H1 (post-signup):** «Hire Your First AI Team»
- **Sub:** «Teamly is not another chatbot. Pick a workflow team with specialist agents, shared context, tool access, and a concrete output.»

- **Hero CTA:** Talk-to-Coordinator (input + chips)
- **Steps headline:** «Three simple steps to your AI team»
  - Step 1 «SUBSCRIBE» — Choose a plan
  - Step 2 «HIRE YOUR TEAM» — «Build your AI department at 10x less than traditional cost.» («$5/agent vs $50/hr»)
  - Step 3 «ASSIGN TASKS» — «Give them tasks and watch your team's productivity multiply.»

## Voice / tone

- **Punchy, founder-y, slightly retro** (matches pixel-art aesthetic)
- Tagline-style: "real agents, real tasks, real results" / "the sweet spot" / "full hustle"
- Tier names имеют game-y feel: «GO ALL IN», «SCALE UP», «GET STARTED», «MOST POPULAR»
- ALL CAPS button labels (retro-style)

## Pricing copy

- TEAMLY 5: «Your first AI workforce — real agents, real tasks, real results.»
- TEAMLY 15 (Most Popular): «The sweet spot — multiple AI teams embedded in your daily workflow.»
- TEAMLY 30: «Full AI workforce — build entire departments around AI teams.»
- ENTERPRISE: «Custom AI infrastructure for organizations with high-volume needs.»

Common: «Every plan includes dedicated infrastructure. Teamly Dollars are used by your agents as they work across Sonnet and Opus. If your team needs more capacity, you can add more Teamly Dollars anytime.»

## Value-stack (5 bullets)

1. **Dedicated infrastructure** (real differentiator: cell per team)
2. **Pre-built workflow teams** (13 ready-to-hire teams)
3. **Watch them work** (Pixel Department UX)
4. **BYOK option** («Save 80%»)
5. **Autonomous mode** (memory + heartbeat + cron — for power users)

## Team-card copy patterns

Каждый team-preset имеет:
- **Icon emoji** (📢 marketing, 💻 dev, 💰 sales, ✍️ writer, …)
- **Name** (Marketing Team)
- **Description** (1 sentence: «SEO, content creation, and campaign strategy»)
- **Detailed description** (2-3 sentences про workflow)
- **Workflow steps** (numbered list)
- **Output** label (что получает клиент)
- **Agents** (pixel-art sprites + names + roles)

Это **content-heavy but scannable** UX, помогает client'у сделать informed выбор.

## Onboarding copy

- «Assign goals» / «Agents coordinate» / «Get deliverables» (3-check value-prop)
- Empty state for catalog: «Ready Teams» / «Search teams...»

## Coordinator wizard copy (post-input)

- «What task do you want to solve?» (Coordinator speech bubble)
- Step 1: «Team size?» (Just me / Small / Growing / Large)
- Step 2: «How should I use the task you described above?» (Use as-is / Adjust plan / Show wide demographic group / Continue research / Back)

Очень structured language — это **decision-tree wizard**, не open chat.

## Payment / BYOK copy

- BYOK pill: «-80%» (large saving callout)
- BYOK headline: «STRETCH YOUR TEAM BUDGET»
- BYOK body: «Bring your own API key below and you'll only pay for raw compute costs. No markup on tokens — just connect your key and your team budget goes much further.»

Это **honest pricing transparency**: «no markup» — большой trust-builder для technical users.

## Cookie/Privacy/Compliance

Не открывали полностью, но визуально:
- Cookie consent banner — стандартный
- Footer links: Privacy / Terms / Cookies / Licenses
- Compliance level — US/EU-focused (нет ФЗ-152 mention)
- Sentry в DE-region (Frankfurt) — указывает на EU-aware data residency policy
- Composio handles 3rd-party OAuth — упрощает privacy claims

## Status / incident communication

В localStorage наблюдали ключ `teamly-incident-banner-2026-05-08` — то есть **8 мая 2026 был incident**, и его dismissal-флаг сохранён. Это **показательно для UX-зрелости**: incident communication через banner (dismissable).

## Что НЕ присутствует в маркетинге

- Case studies / customer logos (no «trusted by» logos на landing)
- Specific ROI numbers (нет «saved $X», «10x output»)
- Reviews / testimonials
- Demo video (только pixel-art animation на landing)
- Blog / content marketing
- Founder story / about page (не открывали)
- Detailed comparison vs competitors (CrewAI, Lindy, Relevance, и т.д.)

Это **early-stage SaaS feel** — продукт продаёт себя через design+features, не через social proof.

## SEO / content keywords (из meta)

- «AI agents»
- «managed hosting»
- «cloud»
- «Pixel Department»
- «zero infrastructure»

Targeting: developers / SaaS-buyers / AI-curious SMB. Не targeting non-technical decision-makers.

## Tone consistency

Везде используется:
- Verbose pixel-style fonts (Press Start 2P) для headings
- Geist / Geist Mono для body
- Pixel-art аватары (visual identity)
- Retro game-y CTA («GO ALL IN», «SCALE UP», «GET STARTED»)
- Conversational descriptions («the sweet spot», «full hustle»)

Это **strong brand identity** — мгновенно узнаваемый visual+lingual style. Сильный wedge против generic-looking AI tools.

## Что мы должны украсть (legally — patterns, not assets)

1. **Pixel-art aesthetic** — это работает для wow + tech-credibility.
2. **"Hire your AI team"** фрейминг (vs «use AI assistant» / «chat with AI»). Это makes продукт более concrete.
3. **Pre-built workflow teams catalog** + структура (description / workflow / output / agents).
4. **BYOK transparency** («no markup on tokens»).
5. **Tier-naming** (Teamly 5 / 15 / 30 — простое числовое scaling, легко запомнить и обсудить).
6. **Plan-anchor «Most Popular»** badge на mid-tier.
7. **«Three simple steps»** структура value-prop.

## Что мы НЕ копируем

1. USD-pricing (наш ₽).
2. Coordinator wizard на landing для unauthenticated users — у нас иной onboarding flow.
3. Маркетинг-копи на английском.
4. Compliance copy («secure in Polar») — у нас другие payment processors.

## Reuse в нашем content marketing

Можно сделать собственные «pre-built teams» для РФ-вертикалей:
- «SMM-команда» для маркетинг-агентств
- «Селлер-команда» для WB/Ozon
- «Юр.отдел» для типовых задач
- «Бухгалтер-команда» для типовых проводок

С таким же visual approach (pixel-art) и копи в нашем tone.
