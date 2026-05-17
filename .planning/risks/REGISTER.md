# Risks Register

> Активные риски с mitigation, owner, monitoring. Все митигации ссылаются на ADR / phase / процесс.

## Формат записи

```
R-NN. <Название>
- Severity: low / medium / high / critical
- Likelihood: low / medium / high
- Owner: <роль или человек>
- Митигация: <ссылки>
- Monitoring: <метрика и алерт>
```

---

## R-01. Отказ LLM-провайдера (DeepSeek / YandexGPT / GigaChat)

- **Severity:** high · **Likelihood:** medium · **Owner:** Tech Lead
- **Митигация:** [ADR-002](../decisions/ADR-002-llm-gateway.md): multi-provider fallback (DeepSeek → YandexGPT → GigaChat), hot-swap без рестарта, health-check каждые 30 сек, user opt-in failover behavior, prompt caching, юр.оговорки в оферте
- **Monitoring:** health-check каждые 30 сек, status page, метрика `llm_provider_availability`

## R-02. Вредный/некачественный результат high-stakes роли (Юрист/Accountant)

- **Severity:** high · **Likelihood:** medium · **Owner:** Product + Tech Lead
- **Митигация:** [ADR-014](../decisions/ADR-014-security.md): disclaimer в оферте; `requires_human_approval: true` для high-stakes; `domain_scope` + `domain_blacklist` per role; output guardrails (DLP-классификатор); ИП-Бухгалтерия — ВСЕ агенты в approval mode by default ([ADR-017](../decisions/ADR-017-vertical-templates.md)); страхование — Wave 3/4
- **Monitoring:** rate срабатываний guardrails, NPS негативные отзывы, инциденты

## R-03. Обновление промпта роли/template ломает существующих клиентов

- **Severity:** medium · **Likelihood:** high · **Owner:** Tech Lead
- **Митигация:** [ADR-010](../decisions/ADR-010-role-versioning.md): SemVer (patch auto / minor opt-in 14 дней / major notice 30 дней), canary 5/25/100% с auto-rollback, golden dataset regression per vertical-template (30-50 задач), fork-наследование security-патчей
- **Monitoring:** canary метрики (success rate, thumbs, latency), golden dataset pass-rate

## R-04. Runaway costs (autonomous mode + agent loops)

- **Severity:** high · **Likelihood:** high · **Owner:** Tech Lead + Founder
- **Митигация:** [ADR-002](../decisions/ADR-002-llm-gateway.md), [ADR-019](../decisions/ADR-019-vertical-autonomous-mode.md): per-cell daily budget hard-cap, per-ritual per-day max executions, kill-switch при spend-rate threshold, deadman switch для autonomous (7 дней без owner activity → pause), курсовая оговорка в оферте (порог 15%)
- **Monitoring:** дашборд маржи per cell/template/agent, алерт при <30% средней маржи

## R-05. Утечка данных через агента / инсайдера / коннектор

- **Severity:** critical · **Likelihood:** medium · **Owner:** Security + Tech Lead
- **Митигация:** [ADR-014](../decisions/ADR-014-security.md): RBAC 5 уровней, DLP-сканер на выходе MCP-tools, изоляция memory от tool-output, операционная гигиена (zero standing access, JIT-доступ, шифрование backup, audit ПДн, 2FA, immutable log, ISO/SOC roadmap); Pyodide мitigates для analytics (всё в браузере клиента, [ADR-020](../decisions/ADR-020-pyodide-code-execution.md)); Cell-level isolation ([ADR-009](../decisions/ADR-009-multitenancy-3-levels.md)); **deployed Phase 00.1 (Session-2026-05-17):** secrets scanning (gitleaks + trufflehog в CI и pre-commit), `.env` gitignored, dev secrets явно изолированы от staging/prod через PLACEHOLDERS.md
- **Monitoring:** rate DLP-срабатываний, alert на массовую выборку ПДн, audit log review weekly

## R-06. Ошибки/конфликты AI-агентов разработки

- **Severity:** medium · **Likelihood:** high · **Owner:** Tech Lead
- **Митигация:** [ADR-015](../decisions/ADR-015-ai-dev-process.md): Tier-based ревью, CI-gates (SAST/secrets/license/SBOM), AI изолирован от prod, worktree-per-task, cost caps, специализированные роли (Planner/Coder/Tester/Reviewer/Security-Auditor/DevOps); **deployed Phase 00.1 (Session-2026-05-17):** supply-chain CI gates — pip-audit (Python CVE) + npm audit (Node CVE) + pip-licenses + license-checker-rseidelsohn (forbid GPL/AGPL/LGPL) + Trivy filesystem scan + Syft SBOM + Grype vuln scan + Bandit static analysis
- **Monitoring:** PR acceptance rate, bug introduction rate (30-day window), AI cost per PR

## R-07. Резкие пики/спады нагрузки

- **Severity:** medium · **Likelihood:** medium · **Owner:** DevOps
- **Митигация:** capacity baseline + rate-limits per тариф + приоритетная очередь; circuit breakers с 4 уровнями (Green/Yellow/Orange/Red); DDoS-Guard + SmartCaptcha; load forecasting + chaos — Wave 3+
- **Monitoring:** queue depth, p95 latency, provider error rate, status page

## R-08. Регуляторные изменения (152-ФЗ, AI-законы, маркировка)

- **Severity:** high · **Likelihood:** high · **Owner:** Founder + юрист
- **Митигация:** Compliance-by-design слоты в архитектуре (маркировка, XAI, retention, локализация); юр.минимум (ООО РФ + зарубежное юр-лицо в Wave 2+ + РКН-уведомление в Wave 0 + товарный знак); полный legal review — roadmap; ru-only stack option ([ADR-018](../decisions/ADR-018-deepseek-primary-llm.md)) для гос-сектора
- **Monitoring:** quarterly legal review, мониторинг РКН/Минцифры новостей

## R-09. Потеря ключевого члена команды / выгорание

- **Severity:** medium · **Likelihood:** medium · **Owner:** Founder
- **Митигация:** Knowledge management (ADR + runbook'и + OWNERS.md); AI как knowledge base (claude-mem/project memory); малая команда + AI-leverage; bus week practice
- **Monitoring:** quarterly 1:1, exit interviews, sentiment в weekly retro

## R-10. Конкуренция (big tech + open-source + демпинг)

- **Severity:** medium · **Likelihood:** high · **Owner:** Founder + Product
- **Митигация:** Network effects через vertical-templates ([ADR-017](../decisions/ADR-017-vertical-templates.md)); data lock-in (workspace memory + Знания команды); 5 vertical-templates как primary moat; value-ladder vs price war; партнёрства; community/бренд — Wave 2; IP — выборочно
- **Monitoring:** competitive intelligence quarterly; defensible metrics (vertical-templates × active cells × ritual usage)
- **Kill criteria для template-каталога** (revised 2026-05-15 — wave-shifts учтены):
  - `productivity-core` (horizontal, W0+): <30% trial users select horizontal vs vertical → проверка к Wave 2 public beta
  - Marketing-agency (W1+): <8% trial к Wave 3
  - Telegram-крейтор (W1+): <5% trial к Wave 3
  - WB-Селлер (W2+): <10% trial к Wave 3
  - ИП-Бухгалтерия (W3+): <3% trial к Wave 4
  - СМБ-Sales (W3+): <8% trial к Wave 4

## R-11. Низкая активация и retention / churn

- **Severity:** high · **Likelihood:** high · **Owner:** Product + CS
- **Митигация:** Automated engagement (14-day journey); Health Score + proactive outreach; образовательный контент; founder-led CS на W0-1; community/AI-Coach/win-back — следующие волны; TTFV <3 мин target через Coordinator wizard + auto-spawn ([ADR-022](../decisions/ADR-022-coordinator-wizard-llm-hybrid.md))
- **Monitoring:** TTFV, trial→paid conversion, monthly churn, NPS, Health Score distribution

## R-12. Недостаток ресурсов / scope creep / отсутствие фокуса

- **Severity:** critical · **Likelihood:** high · **Owner:** Founder
- **Митигация:** must/nice разделение per волна; Build-Measure-Learn loops; ICE prioritization; decision log + kill criteria; Quarterly Strategic Review; lightweight delivery. **Note:** financial runway / burn-management — founder-personal decision out-of-scope project docs per Session-2026-05-15; project tracks AI dev cost caps только в `.claude/agents/_shared/cost-budget.yaml`.
- **Monitoring:** weekly progress vs plan; quarterly strategic review; AI dev cost telemetry per cost-budget.yaml

## R-14. Pixel-art bottleneck

- **Severity:** medium · **Likelihood:** medium · **Owner:** Founder + Designer
- **Митигация:** [ADR-021](../decisions/ADR-021-ai-generated-pixel-pipeline.md): AI-generated baseline (24 archetypes) через SDXL+Pixel-Art-XL LoRA, 5 vertical-героев hand-drawn (~$3-5K total)

## R-16. BYOK ARPU pressure

- **Severity:** medium · **Likelihood:** high · **Owner:** Founder
- **Митигация:** Двухставочный pricing: managed full-margin (~5×), BYOK platform-fee only (~$9/mo fixed per agent); marketing «BYOK = -80% на токены» для price-sensitive segment, managed для quality-first
- **Monitoring:** ARPU per tariff per mode, BYOK adoption rate

## R-17. Anthropic / OpenAI TOS-issues с прокси-аккаунтами

- **Severity:** medium · **Likelihood:** medium · **Owner:** Tech Lead
- **Митигация:** Wave 2+ — Western стек только через BYOK preferred (клиент платит Anthropic напрямую); собственный managed-режим в Wave 2+ только если найдём whitelisted-provider; ru-only / China-only режим для гос-сектора

## R-18. Open-source MCP-серверы maintenance

- **Severity:** low · **Likelihood:** medium · **Owner:** Tech Lead
- **Митигация:** [ADR-013](../decisions/ADR-013-mcp-protocol.md): fork-план для critical community MCP-servers (GitHub, Notion, Slack); наши РФ-MCP — full IP ownership

## R-19. Autonomous mode legal consent

- **Severity:** medium · **Likelihood:** medium · **Owner:** Founder + юрист
- **Митигация:** [ADR-019](../decisions/ADR-019-vertical-autonomous-mode.md): explicit opt-in checkbox при включении autonomy; clear list of actions; юр.copy в оферте; deadman switch
- **Monitoring:** opt-in conversion rate, complaint rate

## R-20. РФ-API instability (общий — SLA, latency, rate-limit, partial outages)

- **Severity:** medium · **Likelihood:** medium · **Owner:** Tech Lead
- **Scope:** Верхнеуровневый риск надёжности всех РФ-API, на которых строится продукт (WB Партнёры, Ozon Seller, 1С REST, Эльба, ЮKassa, Yandex 360, Telegram Bot API, MCP-серверы партнёров). Покрывает SLA-degradation, latency-spikes, rate-limit изменения, региональные partial-outages, провайдерские maintenance windows. **Контрактные/schema breaking changes — см. R-30.**
- **Митигация:** Health-check каждые 5 минут на per-API basis; при >5% error rate → auto-pause связанных rituals + alert owner; circuit-breakers (4 уровня Green/Yellow/Orange/Red); graceful degradation с user-visible status; per-API capacity baseline + retry-with-backoff. Status-page для пользователей.
- **Monitoring:** per-MCP-server availability, error rate, p95 latency, rate-limit hit ratio

## R-21. Self-hosted auth security ownership

- **Severity:** medium · **Likelihood:** low · **Owner:** Tech Lead + Security
- **Митигация:** [ADR-007](../decisions/ADR-007-authentik-then-keycloak.md): bcrypt cost 12+, JWT short TTL, refresh rotation, rate-limit, HIBP-check (Wave 1), 2FA mandatory для Owner/Admin, pen-test перед public-launch (Wave 2), audit log; migration на Logto в Wave 2-3 при расширении requirements

## R-22. Auth migration window vulnerability (Wave 2-3)

- **Severity:** low · **Likelihood:** low · **Owner:** Tech Lead
- **Митигация:** [ADR-007](../decisions/ADR-007-authentik-then-keycloak.md): migration-tool заранее (Phase 04.12), dry-run в staging, bcrypt-hashes совместимы, маintenance window <2 часа

## R-23. AI-generated assets copyright

- **Severity:** low · **Likelihood:** low · **Owner:** Founder + юрист
- **Митигация:** [ADR-021](../decisions/ADR-021-ai-generated-pixel-pipeline.md): Pixel-Art-XL LoRA с verified dataset; manual cleanup (Aseprite) добавляет creative-input; generated assets — наша собственность; legal-review каждого выпуска

## R-24. Visual consistency между AI-generated archetypes

- **Severity:** low · **Likelihood:** medium · **Owner:** Designer
- **Митигация:** [ADR-021](../decisions/ADR-021-ai-generated-pixel-pipeline.md): один LoRA + жёсткий prompt-template + manual cleanup pass per archetype

## R-25. Trial abuse (free credits exploitation)

- **Severity:** medium · **Likelihood:** high · **Owner:** Tech Lead
- **Митигация:** [ADR-022](../decisions/ADR-022-coordinator-wizard-llm-hybrid.md): email verification mandatory + IP/device fingerprinting + free-trial throttling (1 trial per email/IP/device); hard-cap 500 кредитов на trial
- **Monitoring:** trial-spawn rate per IP/email, abuse-pattern detection

## R-26. Trial-cell provisioning cost

- **Severity:** medium · **Likelihood:** high · **Owner:** DevOps
- **Митигация:** Aggressive auto-cleanup unused trials через 14 дней; sandbox-pool sharing для trials; logical cells без dedicated physical infra ([ADR-009](../decisions/ADR-009-multitenancy-3-levels.md))
- **Monitoring:** active trials count, conversion rate, infra cost per trial

## R-27. Pyodide compatibility / version drift

- **Severity:** low · **Likelihood:** medium · **Owner:** Senior Frontend
- **Митигация:** [ADR-020](../decisions/ADR-020-pyodide-code-execution.md): pin Pyodide version, monitor compatibility tests, опциональный server-side fallback в Wave 3

## R-28. Слабые клиентские устройства (Pyodide на mobile)

- **Severity:** medium · **Likelihood:** medium · **Owner:** Senior Frontend
- **Митигация:** [ADR-020](../decisions/ADR-020-pyodide-code-execution.md): detect device capabilities + UX «desktop recommended for heavy analysis»; opt-in server-side execution в Wave 3 для больших jobs

## R-30. WB/Ozon API contract/schema breaking changes

- **Severity:** medium · **Likelihood:** medium · **Owner:** Tech Lead
- **Scope:** Узкий риск contract/schema breakage на vertical-критичных API маркетплейсов (WB Партнёры, Ozon Seller, 1С REST, Эльба): deprecated endpoints, новые required fields, изменения авторизации, удалённые ресурсы. Отличается от R-20 (operational instability) тем, что требует code change на стороне MCP-сервера. Касается ровно тех vertical-templates, которые на эти API завязаны (WB-Селлер, ИП-Бухгалтерия).
- **Митигация:** [ADR-019](../decisions/ADR-019-vertical-autonomous-mode.md): dedicated MCP-server monitoring + auto-fallback to «degraded mode» с явным user-сообщением + semantic-versioning для наших MCP-серверов (мажорный bump провайдера → guarded rollout); contract-tests в CI на golden API-fixtures.
- **Monitoring:** MCP-server health post-deploy, contract-test pass-rate, days-since-last-provider-changelog

## R-29. Founder vertical expertise gap — claim vs reality для 5 vertical-templates

- **Status:** `closed (resolved)` — 2026-05-13
- **Severity (когда был open):** high · **Likelihood (когда был open):** medium · **Owner:** Founder
- **Rationale закрытия:** Founder operates as real-world expert across all 5 vertical-templates (WB-Селлер, Marketing-Агентство, TG-Крейтор, ИП-Бухгалтерия, SMB-Sales). Vertical-template content validation gate handled через [ADR-026](../decisions/ADR-026-vertical-expertise-pipeline.md): founder-review checklist + evaluator gate (≥75% golden-dataset pass + 100% adversarial probes) + Wave 1+ friend-loop (3-5 ICP-friends × 5 задач) + 90-day re-verification cycle. См. [ADR-028 §decision-6](../decisions/ADR-028-policies-registry.md#decision-6).
- **Monitoring (на случай re-opening):** evaluator pass-rate < 75% подряд 2 цикла на одной вертикали → перевести обратно в `open` + флаг founder.

## R-31. AI-cost overrun under 11-Opus persistent team

- **Severity:** high · **Likelihood:** high · **Owner:** Founder
- **Митигация:** [ADR-023](../decisions/ADR-023-ai-team-runtime.md) Consequences + `.claude/agents/_shared/cost-budget.yaml` (Milestone B). Cap policy (per-task / per-day / per-team monthly limits + tier-1 Sonnet fallback rules) — задаётся founder'ом в `cost-budget.yaml`; конкретные числа не зашиваются в этот ADR/REGISTER. Operational guardrail — 30-min stagnation kill-switch ([ADR-015 §5](../decisions/ADR-015-ai-dev-process.md)). Cost telemetry — Langfuse dev-instance.
- **Trigger re-evaluation:** sustained burn above founder-defined threshold → escalate founder, переоценить fallback policy в `cost-budget.yaml`.
- **Monitoring:** monthly spend per role, ratio Opus/Sonnet invocations, kill-switch trigger count

## R-32. Master-Agent layer cost & latency overhead (W1+ vertical-templates)

- **Opened:** 2026-05-15 (per Session-2026-05-15 + [ADR-029](../decisions/ADR-029-master-agent-vertical-templates.md))
- **Severity:** medium · **Likelihood:** medium · **Owner:** Tech Lead + Founder
- **Scope:** Master-Agent layer добавляет +1 LLM-call per vertical task (~+15–20% tokens, +1–3 sec latency) над horizontal baseline. Cascading scenarios: Master → Coordinator → 3 parallel specialists может accidentally trigger >50 T-credit budget cap. Affects TTFV для vertical-trials (Wave 2 ≤3 min target).
- **Митигация:** [ADR-029](../decisions/ADR-029-master-agent-vertical-templates.md) §«Cost & latency budget»: per-task budget cap 50 T-credits applies к Master+children-chain совокупно (не per agent); Wave 1 phase 01.1 acceptance criteria explicitly verify это; Master-prompts оптимизированы под short reasoning chains (strategic plan ≤500 tokens); fallback на horizontal preset при `master_failed` event.
- **Monitoring:** p95 latency per vertical task vs horizontal baseline; Master-Agent token-cost rollup; budget-cap-trigger rate

## R-33. Telegram Business API privacy / 152-ФЗ exposure

- **Opened:** 2026-05-15 (per Session-2026-05-15 + [ADR-030](../decisions/ADR-030-telegram-business-api.md))
- **Severity:** critical · **Likelihood:** low (с mitigation) → medium (без) · **Owner:** Founder + Security + юрист
- **Scope:** Bot читает private DM-переписку пользователя через Telegram Business API (W1 phase 01.10). Утечка / unauthorized retention / leakage в LLM-логи = критический репутационный hit + потенциальная 152-ФЗ нарушение + РКН-санкции.
- **Митигация:** [ADR-030](../decisions/ADR-030-telegram-business-api.md): explicit consent UX (3-checkbox flow + opt-in для auto-reply/reactions); ephemeral retention ≤7 days default; encryption at rest per cell-key (`pgcrypto`); 100% audit log с consent_id; РКН-уведомление update (OQ-33); 152-ФЗ disclosure в Privacy Policy (OQ-32); revoke flow ≤30s.
- **Monitoring:** consent-flow completion rate, retention-purge job success rate, audit-log integrity check daily, DLP-trigger rate on DM content

## R-34. LLM-only Analyst hallucination (Wave 0 horizontal preset)

- **Opened:** 2026-05-15 (per Session-2026-05-15 — Wave 0 Analyst без Pyodide)
- **Severity:** medium · **Likelihood:** medium · **Owner:** Tech Lead
- **Scope:** Analyst роль в Wave 0 работает LLM-only без Pyodide code-execution. Numerical estimates (TAM/SAM, KPI projections, ROI) — pure reasoning без вычислений. Risk: hallucinated точечные числа без supporting math; пользователь принимает решения на основе фальшивых данных.
- **Митигация:** [Phase 00.5](../roadmap/wave-0-foundation/phases/00.5-pydantic-ai-productivity-team.md) AC + [`contracts/role-prompts/analyst.md`](../contracts/role-prompts/analyst.md) explicit requirements:
  - Все numerical claims с явными assumption-lists
  - Range estimates вместо точечных («TAM 50–80M USD», не «TAM 67M»)
  - Verifiable sources для всех ключевых чисел
  - Capability-gap callouts с пометкой «Phase 02.X (Pyodide) бы дал точный расчёт»
  - Self-eval checklist enforced в prompt
  - Wave 2 closure: Pyodide добавляется per [ADR-020](../decisions/ADR-020-pyodide-code-execution.md); R-34 closeable когда Analyst migrated на Pyodide для quantitative tasks
- **Monitoring:** ad-hoc audit demo-runs на наличие assumption-lists; user feedback log на «Analyst дал неверное число» категории

---

## Стратегические ставки (с kill criteria)

| Ставка | Continue criteria | Kill criteria | Срок |
|---|---|---|---|
| **`productivity-core` (horizontal) как Wave 0 entry-USP** | ≥30% trial-юзеров завершают «Market & content brief» сценарий + ≥30% выбирают horizontal над vertical в каталоге к Wave 2 | <15% completion / <10% horizontal-share к Wave 2 | 4 мес после Wave 0 |
| Маркетинг-агентство как Vertical-1 (W1 anchor) | 25%+ trial к Wave 2 | <8% к Wave 3 | 6 мес |
| Telegram-крейтор как Vertical-2 (W1) | 20%+ trial к Wave 2 (boosted by Business API DM-management) | <5% к Wave 3 | 6 мес |
| WB-Селлер как Vertical-3 (W2 anchor) | 25%+ trial из WB-вертикали к Wave 3 | <10% trial к Wave 3 | 4 мес после Wave 2 |
| ИП-Бухгалтерия как Vertical-4 (W3) | 10%+ trial к Wave 4 | <3% к Wave 4 | 9 мес |
| СМБ-Sales как Vertical-5 (W3) | 15%+ trial к Wave 4 | <8% к Wave 4 | 9 мес |
| **Master-Agent layer как vertical-pricing-rationale** | Vertical-tier conversion rate ≥1.5× horizontal-tier; cost-overhead absorbed by margin | Vertical-tier converts at same rate as horizontal (no premium-rationale) | 4 мес после Wave 1 |
| **Telegram Business API как Wave 1 hook** | ≥30% Wave 1 friends активируют Business-bot; ≥50% retention week-4 | <10% activation / privacy incident | 4 мес после Wave 1 |
| DeepSeek как primary LLM | Маржа платформы >40% на DeepSeek-задачах | <20% маржи; политические блокеры | 6 мес |
| MCP-протокол как connector layer | 10+ MCP-servers активных к Wave 3 | <5 к Wave 3 | 8 мес |
| Pixel Department как secondary USP | NPS upticks от Pixel mentions | NPS <30 + 0 упоминаний в отзывах | 4 мес после Wave 2 |
| Autonomous mode (vertical rituals) | Используется >25% paid teams | <10% использования к Wave 4 | 6 мес после Wave 3 |

## Quarterly Review

Каждый квартал:
1. Pass по всем R-NN: статус, monitoring metrics, изменения severity/likelihood
2. Pass по стратегическим ставкам: continue/kill/pivot
3. Новые риски этого квартала
4. Закрытые риски этого квартала
