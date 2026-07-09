---
title: "Domain Research Brief: Telegram-крейтор (RU Telegram content creator)"
vertical_slug: telegram_creator
version: 0.1.0
last-updated: 2026-07-09
status: draft
research-method: "AI-baseline, WebSearch-grounded (grill research-first requirement, ADR-026 amendment)"
---

# Domain Research Brief — Telegram-крейтор

> Grill-mandated research-first step (ADR-026 amendment, §7): before authoring
> the Master-prompt / role-prompts / golden-dataset for a new vertical, produce
> a cited domain brief. This is the AI-baseline research pass for
> `telegram_creator` (Phase 01.10, second Wave-1 vertical per
> [ADR-017](../../decisions/ADR-017-vertical-templates.md)). Founder review +
> personal-operating-expertise edit (Pattern-D step 2) is a separate,
> founder-owned step — this brief does not substitute for it.

## 1. ЦА (ICP) — who is the Telegram-крейтор

**Definition (per [ADR-017](../../decisions/ADR-017-vertical-templates.md)):** an author running a monetized Telegram channel — "Telegram-каналы 50K+ авторов с monetization." In practice the addressable market is far broader: Telemetr's 2024 admin survey found that **useful monetization signals appear from as few as 300-500 loyal, engaged readers**, not only at the 50K+ tier — so the product ICP spans micro-creators (1K-10K), mid-tier creators (10K-100K), and established creators (100K+) ([Tribute, "Монетизация ТГ канала в 2026"](https://tribute.tg/blog/monetizaciya-telegram-kanalov-kak-podklyuchit-i-zarabatyvat-v-2026-godu); [vc.ru, "Как монетизировать Telegram-канал в 2026 году"](https://vc.ru/telegram/2699561-monetizatsiya-telegram-kanala)).

**Persona shape (Telemetr 2024 admin research):**
- Most admins run a **personal/authorial channel** (own voice, own name) — the single most common channel type, ahead of news and education channels ([Likeni.ru summary of Telemetr 2024](https://www.likeni.ru/analytics/adminy-telegram-kanalov-kto-oni-skolko-zarabatyvayut-i-kak-prodvigayut-proekty-issledovanie-telemetr/)).
- A large share of monetizing admins are **self-employed (самозанятые)** — reported at 41.1% among admins who earn from their channel — which shapes how the product should talk about pricing/invoicing (НПД tax regime, not a legal entity) ([Likeni.ru / Telemetr 2024](https://www.likeni.ru/analytics/adminy-telegram-kanalov-kto-oni-skolko-zarabatyvayut-i-kak-prodvigayut-proekty-issledovanie-telemetr/)).
- **More than half of admins who actively monetize work in a team of 2+** (creator + editor/SMM/ad-manager) rather than solo — i.e. the product should assume the creator sometimes delegates drafting/scheduling, which matches our Master→Coordinator→specialists shape ([Likeni.ru / Telemetr 2024](https://www.likeni.ru/analytics/adminy-telegram-kanalov-kto-oni-skolko-zarabatyvayut-i-kak-prodvigayut-proekty-issledovanie-telemetr/)).
- Telegram's own core audience skews toward higher education, IT/marketing-heavy professions — a well-informed, save-and-refer-heavy reader base rather than a casual scroll-feed audience (longstanding finding, reconfirmed as still broadly true) ([vc.ru, "Портрет наиболее активной аудитории Telegram в России"](https://vc.ru/marketing/25614-audience-of-telegram)).

**Pains (JTBD-shaping):**
1. Keeping a content calendar consistent without burning out — "what do I post today" fatigue is the #1 operational drag for a solo/small-team channel.
2. Turning one piece of research/expertise into multiple formats (post → story → follow-up) without redoing the work each time.
3. Reading the numbers correctly — TGStat/Telemetr-style metrics (ERR, reach, subscriber churn) are available but time-consuming to interpret without a dedicated analyst.
4. Not fabricating results to sponsors/advertisers, and not accidentally breaking RU ad-marking law when running sponsored posts.
5. Deciding *how* to monetize (sponsored posts vs Telegram Stars subscription vs own digital product) at their specific size and niche.

## 2. Поведенческий паттерн — how a Telegram creator actually operates

- **Cadence:** most guidance converges on **~1 post/day** as the sustainable default for a solo creator, with **3-5 posts/week** acceptable for smaller/side-project channels; multi-post-per-day is reserved for news/aggregator-style channels, not personal-brand ones ([tg-telegram.blog content-plan guide](https://tg-telegram.blog/kontent-plan-dla-telegram-kanala-kakie-formaty-i-skol-ko-publikovat-v-den); [vc.ru "Контент-план для Telegram-канала в 2025"](https://vc.ru/marketing/1842354-kontent-plan-dlya-telegram-kanala-v-2025-kak-chasto-postit-chtoby-ne-slit-ohvaty)).
- **Rubrication:** creators commonly pin recurring rubrics to specific weekdays (e.g. Monday = expert take, Wednesday = case/story, Friday = engagement/poll) to keep a content plan predictable for both the author and the audience ([Remarka Agency content-plan guide](https://remarka.agency/journal/kontent-plan-dlya-telegramm-kanala-shablon-idei-rubrik-formati-kontenta)).
- **Planning horizon:** a month-level rubric skeleton + a rolling 2-week detailed plan is the common practice — detailed enough to stay consistent, loose enough to react to trending topics ([1ps.ru, "30 видов контента для Телеграма"](https://1ps.ru/blog/texts/2025/v-poiskax-vdoxnoveniya-30-tipov-kontenta-v-telegram-kotoryie-czeplyayut-podpischikov/)).
- **No black-box algorithm to game.** Unlike TikTok/Instagram, Telegram delivers posts to subscribers roughly in full (no engagement-based feed-ranking gate on discovery within a channel) — so the operative growth levers are (a) reader-to-reader forwards/reposts, (b) cross-channel ad placements, and (c) direct recommendation/search, not "beating the algorithm." This reframes what a creator's AI team should optimize for: forward-worthiness and subscriber retention over raw novelty.
- **Analytics literacy is inconsistent.** TGStat and Telemetr are the two dominant RU analytics services; ERR (engagement rate by reach) is the standard engagement metric, but interpreting it against category benchmarks is a skill most solo creators lack — normal ERR bands are roughly **10-30% for channels under 10K subscribers** and **5-15% for channels in the 10K-100K range**, so a 6% ERR reads very differently for a 5K-subscriber channel (weak) than a 80K-subscriber one (healthy) ([TGStat analytics overview](https://tgstat.ru/en/analytics)).

## 3. Ключевые аспекты — content formats, cadence, engagement, monetization, RU specifics

### 3.1 Content formats (2025-2026 baseline)

- **Text post** — the base unit; short and scannable is consistently favored over long-form in 2025 guidance ([1ps.ru](https://1ps.ru/blog/texts/2025/v-poiskax-vdoxnoveniya-30-tipov-kontenta-v-telegram-kotoryie-czeplyayut-podpischikov/)).
- **Stories** (Telegram's native stories surface) — used as a distinct promotional/teaser format, not a post replacement ([sky.pro content-strategy overview](https://sky.pro/wiki/profession/kontent-dlya-telegram-kanala-chto-publikovat/)).
- **Кружки (round video messages)** — used for a personal-voice touch that text can't replicate ([1ps.ru](https://1ps.ru/blog/texts/2025/v-poiskax-vdoxnoveniya-30-tipov-kontenta-v-telegram-kotoryie-czeplyayut-podpischikov/)).
- **Polls / quizzes / games** — the standard engagement-lift mechanic ([1ps.ru](https://1ps.ru/blog/texts/2025/v-poiskax-vdoxnoveniya-30-tipov-kontenta-v-telegram-kotoryie-czeplyayut-podpischikov/)).
- **Digests, lifehacks, reviews, case studies, client/reader testimonials** — the recurring "always works" content buckets cited across multiple 2025 guides ([1ps.ru](https://1ps.ru/blog/texts/2025/v-poiskax-vdoxnoveniya-30-tipov-kontenta-v-telegram-kotoryie-czeplyayut-podpischikov/); [vadstudio "30 идей контента для Telegram"](https://vadstudio.md/info/30-idej-kontenta-dlya-telegram-trendy-2025/)).

### 3.2 Monetization channels (what our Master needs to reason about)

1. **Sponsored posts (реклама/интеграции)** — the classic model. Entry threshold cited as low as **1,000-1,500 subscribers**; a **10,000-subscriber channel with 20-30% engagement** publishing 2-3 sponsored posts/week can realistically earn **≈30,000-90,000 ₽/month** ([vc.ru, "Как монетизировать Telegram-канал в 2026 году"](https://vc.ru/telegram/2699561-monetizatsiya-telegram-kanala)).
2. **Telegram's official ad-revenue-share program** — Telegram pays creators **50% of the ad revenue** generated by native ads shown in their channel, one of the more generous creator-revenue-shares in social media ([vc.ru, "Как монетизировать Telegram-канал в 2026 году"](https://vc.ru/telegram/2699561-monetizatsiya-telegram-kanala)). The RU-market complement is the **Yandex Advertising Network** integration — over **3,000 new Telegram channels connected from February 2026 onward**, and **67% of surveyed advertisers named Telegram a priority influencer-marketing channel through end-2026** ([vc.ru, "Как монетизировать Telegram-канал в 2026 году"](https://vc.ru/telegram/2699561-monetizatsiya-telegram-kanala)).
3. **Telegram Stars — paid posts / paid subscription** — creators can mark individual posts as pay-to-unlock, or run a recurring paid-subscription tier (priced in Stars, e.g. 100-300 Stars/month), with **creators keeping 100% of the Stars value** (no Telegram platform cut on the Stars themselves) and a **~3-week hold before withdrawal, 1,000-Star minimum payout** ([vc.ru, "Как использовать Telegram Stars для монетизации"](https://vc.ru/telegram/2727592-monetizatsiya-telegram-kanalov-i-botov-s-pomoshchyu-stars)).
4. **Own digital product** (courses, consulting, community access) sold through the channel — the natural next step once an audience trusts the creator; this is the "Курс-автор" half of the ADR-017 persona name.

### 3.3 RU regulatory specifics (hard constraints for the domain, not optional style choices)

- **Ad-marking law applies to Telegram exactly as it does to any other RU media.** §38-FZ (закон о рекламе) draws no platform exception — Telegram, WhatsApp, Viber posts are treated the same as a website or classic media placement the moment money changes hands for a post ([mosartcentre.ru, "Реклама в Telegram-каналах: законы и маркировка РФ"](https://mosartcentre.ru/i/6/chto-nuzhno-znat-o-reklame-v-telegram-kanalah/)). Every sponsored post needs: the label **«Реклама»**, the advertiser's name + INN, and an **erid token** issued through an ОРД (Оператор Рекламных Данных), which reports into Roskomnadzor's ЕРИР (Единый реестр интернет-рекламы) ([ord-a.ru explainer](https://ord-a.ru/help/wiki/korotko-o-novom-zakone/); [Habr, "Маркировка Телеграм-рекламы в 2025"](https://habr.com/ru/articles/976498/)). Roskomnadzor's automated enforcement ("Робот РКН") is materially active: **376 fine rulings totalling ≈24.4M ₽ in a 14-month window** through 2025 ([Habr](https://habr.com/ru/articles/976498/)).
- **Blogger registry (РКН реестр блогеров).** Since **1 November 2024**, any RU channel/page/account with **10,000+ subscribers** — Telegram explicitly named alongside VK, OK, Dzen, Rutube, Pikabu, etc. — must self-report to Roskomnadzor's blogger registry within **10 business days** of crossing the threshold. Failing to register blocks the ability to run ads or accept donations on that channel and blocks others from reposting it; fines range **2,000-2,500 ₽ (individuals)** up to **100,000-500,000 ₽ (legal entities)** ([elama.ru registration guide](https://elama.ru/blog/registraciya-blogerov-v-roskomnadzore-gayd-po-novomu-zakonu/); [Skillbox Media](https://skillbox.ru/media/marketing/na-vashey-stranice-10-tysyach-podpischikov-chto-delat-chtoby-ee-ne-zablokirovali/)). This is a **domain constraint the Master must proactively surface** once a creator's audience approaches 10K — a channel-specific analog to the marketing-agency vertical's ad-marking guardrail.
- **Self-employment (самозанятость/НПД) is the default tax posture** for the majority of monetizing creators (per the Telemetr 41.1% figure above), which should inform how the team frames pricing/invoicing advice — it is operational guidance, not legal/tax advice, and the team must not present itself as a substitute for an accountant or lawyer.

### 3.4 Engagement measurement

- **ERR (Engagement Rate by Reach) = (reactions + reposts) / reach × 100%** is the RU-market standard engagement metric (TGStat/Telemetr convention), distinct from ER-by-subscribers ([TGStat analytics](https://tgstat.ru/en/analytics)).
- Category-relative benchmarks matter more than an absolute ERR number: **10-30% is healthy under 10K subscribers**, **5-15% is healthy in the 10K-100K band** — the same raw ERR can be a red flag or a strong result depending on channel size ([TGStat analytics](https://tgstat.ru/en/analytics)).

## 4. Implications for the Master-Agent + team design

- The Master ("CEO of the creator's Telegram business") must default every plan to **RU-legal-aware, RU-market-aware guidance**: ad-marking (ОРД/erid/ЕРИР) the moment a post is sponsored, and the **10K-subscriber РКН blogger-registry trigger** as a proactive flag, not something the creator has to ask about.
- The team needs a **channel-facing specialist** distinct from the horizontal Writer/Researcher — one that reads what is actually happening on the channel (comments, reactions, DMs) and prepares Telegram-native drafts, without ever being allowed to autonomously *send* to the channel (send-side stays behind the approval-UI gate, per [`src/security/capability.py`](../../../backend/src/security/capability.py) `TOOL_RISK` — `telegram_read_updates` = READ_ONLY, `telegram_draft_message` = INTERNAL, `send_telegram` = DANGEROUS/deny-until-approval).
- Monetization guidance must **never fabricate a revenue estimate** for a specific creator without their actual reach/ERR data — the vc.ru "30k-90k ₽/month at 10K subs + 20-30% ERR" figure above is a *market reference range*, not a guarantee, and the prompts must treat it that way (mirrors the marketing-agency Master's "don't fabricate KPIs" guardrail).
- Content-repurposing (one research pass → post + story + follow-up) is a first-class workflow, not an afterthought — it maps directly to the Researcher → Writer → Community-manager handoff chain.

## Sources (accessed 2026-07-09)

- [Tribute — «Монетизация ТГ канала в 2026 году»](https://tribute.tg/blog/monetizaciya-telegram-kanalov-kak-podklyuchit-i-zarabatyvat-v-2026-godu)
- [vc.ru — «Как монетизировать Telegram-канал в 2026 году»](https://vc.ru/telegram/2699561-monetizatsiya-telegram-kanala)
- [vc.ru — «Как использовать Telegram Stars для монетизации каналов и ботов»](https://vc.ru/telegram/2727592-monetizatsiya-telegram-kanalov-i-botov-s-pomoshchyu-stars)
- [Likeni.ru — «Админы Telegram-каналов: кто они, сколько зарабатывают» (Telemetr 2024 research summary)](https://www.likeni.ru/analytics/adminy-telegram-kanalov-kto-oni-skolko-zarabatyvayut-i-kak-prodvigayut-proekty-issledovanie-telemetr/)
- [vc.ru — «Портрет наиболее активной аудитории Telegram в России»](https://vc.ru/marketing/25614-audience-of-telegram)
- [TGStat — Аналитика Telegram-каналов и чатов (ERR methodology + benchmarks)](https://tgstat.ru/en/analytics)
- [tg-telegram.blog — «Контент-план для Telegram-канала: какие форматы и сколько публиковать в день»](https://tg-telegram.blog/kontent-plan-dla-telegram-kanala-kakie-formaty-i-skol-ko-publikovat-v-den)
- [vc.ru — «Контент-план для Telegram-канала в 2025»](https://vc.ru/marketing/1842354-kontent-plan-dlya-telegram-kanala-v-2025-kak-chasto-postit-chtoby-ne-slit-ohvaty)
- [Remarka Agency — «Контент план для телеграмм канала: шаблон, идеи рубрик»](https://remarka.agency/journal/kontent-plan-dlya-telegramm-kanala-shablon-idei-rubrik-formati-kontenta)
- [1ps.ru — «Контент для Телеграма: 30 видов, которые точно привлекут аудиторию»](https://1ps.ru/blog/texts/2025/v-poiskax-vdoxnoveniya-30-tipov-kontenta-v-telegram-kotoryie-czeplyayut-podpischikov/)
- [vadstudio — «30 идей контента для Telegram: тренды 2025»](https://vadstudio.md/info/30-idej-kontenta-dlya-telegram-trendy-2025/)
- [sky.pro — «Контент-стратегия в Telegram: форматы, планирование, аналитика»](https://sky.pro/wiki/profession/kontent-dlya-telegram-kanala-chto-publikovat/)
- [mosartcentre.ru — «Реклама в Telegram-каналах: законы и маркировка РФ»](https://mosartcentre.ru/i/6/chto-nuzhno-znat-o-reklame-v-telegram-kanalah/)
- [ord-a.ru — «ФЗ о маркировке рекламы в Интернете» (ОРД/ЕРИР/erid explainer)](https://ord-a.ru/help/wiki/korotko-o-novom-zakone/)
- [Habr — «Маркировка Телеграм-рекламы в 2025: что изменилось»](https://habr.com/ru/articles/976498/)
- [elama.ru — «Регистрация блогеров в Роскомнадзоре 2026: пошаговая инструкция»](https://elama.ru/blog/registraciya-blogerov-v-roskomnadzore-gayd-po-novomu-zakonu/)
- [Skillbox Media — «Как блогерам с 10 000 подписчиков передать данные в РКН»](https://skillbox.ru/media/marketing/na-vashey-stranice-10-tysyach-podpischikov-chto-delat-chtoby-ee-ne-zablokirovali/)

## Known gaps / not covered (honest scope limits)

- No first-party TGStat/Telemetr raw dataset access — figures above are as reported in secondary write-ups of those studies, not independently re-derived. Founder review should re-verify against `tgstat.ru/research-2021`-style primary reports if precision matters for a specific claim.
- Telegram Business API (native CRM-style features for creators) is explicitly Wave-2+ scope (see `README.md` out-of-scope note) and is not researched here.
- Pricing benchmarks (₽30k-90k/month example) are a single secondary-source data point, not a distribution — treat as an illustrative range only, never as a per-creator guarantee (see §4 anti-hallucination note).
