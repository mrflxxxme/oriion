"""Canned ModelResponses for the «Market & content brief» demo scenario.

Phase 00.5b Commit 4 — keyed by ``(role_key, scenario_id="market_brief_demo")``.
Content is shape-correct for AC9 assertions (brief ≥1500w RU, competitive
matrix ≥5×4 markdown table, content plan exactly 10 posts).

Each role's bucket is a list walked in order. Every role now has exactly ONE
canned response: the specialists emit their artifact body; the Coordinator
emits a single fenced-JSON ``CoordinatorOutput`` plan (AC-W1-16b plan-then-
execute — it no longer decomposes-then-synthesizes across two calls).

Refining content is fine — the keying + Fail-loud contract is what matters.
The demo-flow integration test asserts artifact shapes against these strings,
so any refinement must keep the AC9 word-count / row-count invariants.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.usage import RequestUsage

SCENARIO_ID = "market_brief_demo"

# ── Researcher canned output ─────────────────────────────────────────────
# Competitive matrix ≥5×4 markdown table + 3+ verifiable sources.
_RESEARCHER_OUTPUT = """\
# Market research: AI-команды для СМБ в РФ

## Конкурентная матрица (5×4)

| Игрок | Сегмент | Сильная сторона | Слабая сторона |
|---|---|---|---|
| ChatGPT Team | Универсальный SMB | Бренд, экосистема плагинов | Нет RU-вертикалей, нет ПДн compliance |
| Anthropic Claude Pro | Enterprise | Длинный контекст, безопасность | Высокая цена, нет RU-аккаунтов |
| Яндекс GPT Team | RU SMB | Локальная инфра, ФЗ-152 | Слабый агентский runtime, нет multi-agent |
| GigaChat Business | RU enterprise | Господдержка, RU NDA | Закрытая платформа, нет MCP |
| Local LLM (LM Studio + open-source) | DIY-комьюнити | Полный контроль, $0 inference | Высокий порог входа, нет команд |

## Ключевые источники

1. [Statista 2025] Российский SMB-рынок AI-инструментов: $480M к концу 2025, CAGR 42%.
2. [RBK 2026-Q1] Adoption rate AI среди РФ-СМБ: 18% (vs. 34% global), gap = vertical templates.
3. [TAdviser 2026-04] Топ-3 барьера: цена ($), интеграция (ru-stack), compliance (ФЗ-152).

## Контекст

Российский рынок AI-команд для СМБ к середине 2026 года сформирован, но
горизонтальные универсальные ассистенты (ChatGPT, Claude) проигрывают
в трёх измерениях: locality (нет RU-вертикалей), compliance (ФЗ-152, РКН),
и стек (Яндекс Cloud, ICQ-style русскоязычная поддержка). Открыта ниша
для «horizontal-then-vertical» позиционирования: универсальная команда
из 4 ролей закрывает 60% бытовых SMB-задач + Master-Agent layer + 5
вертикальных шаблонов закрывают оставшиеся 40% domain-heavy сценариев.
"""


# ── Writer canned output: ≥1500-word RU brief + 10-post content plan ─────
# Brief composed of intro + 5 sections × ~250 words each + conclusion.
_BRIEF_INTRO = """\
# Market & Content Brief: AI-команды для СМБ в РФ

## Резюме

Российский SMB-сегмент к Q2 2026 готов к адаптации AI-команд, но
существующие решения провалены по трём осям: locality, compliance,
интеграция с RU-стеком. Платформа Профики выходит с дуальным
позиционированием «универсальная команда + вертикальные шаблоны»,
закрывающим горизонтальные задачи через productivity-core preset
(Coordinator + Researcher + Writer + Analyst) и domain-heavy сценарии
через Master-Agent layer и 5 RU-вертикалей (Маркетинг-агентство,
Telegram-крейтор, WB-Селлер, ИП-Бухгалтерия, СМБ-Sales).
"""

_BRIEF_SECTIONS = [
    """\
## 1. Рыночный контекст

Российский рынок AI-инструментов для малого и среднего бизнеса в 2025-2026
годах находится на стадии раннего mass-adoption. По данным Statista, объём
сегмента достигнет $480M к концу 2025 года при среднегодовом росте 42%.
Однако adoption-rate среди РФ-СМБ составляет 18% — это вдвое ниже глобального
показателя в 34%. Главные барьеры: (1) ценовая чувствительность —
ChatGPT Team и Claude Pro доступны только через VPN и зарубежные платёжные
системы; (2) отсутствие compliance-стека — большинство игроков не предоставляют
ФЗ-152-conformant обработку персональных данных и не имеют РКН-уведомления
как оператор; (3) разрыв с RU-стеком — Яндекс Cloud, ВКонтакте, Тинькофф API,
1С — типичный SMB живёт внутри этих сервисов, но универсальные ассистенты
не интегрируются. Профики закрывает все три барьера: ценообразование в
рублях через ЮKassa, ФЗ-152-conformant архитектура с RKN-уведомлением как
оператор ПДн, и нативные коннекторы к ключевым RU-сервисам через MCP-протокол.
""",
    """\
## 2. Целевая аудитория и сегментация

Первичный таргет — solo-founders + микрокоманды до 10 человек в трёх
вертикалях: маркетинг-агентства (1500+ зарегистрированных в РФ по данным
ИНИОР), Telegram-крейторы с monetization-stage (около 8 000 активных
каналов с 10K+ подписчиков), и WB-Селлеры (около 700K активных продавцов
на маркетплейсе). Вторичный таргет — ИП-бухгалтерия (1.2M ИП в РФ) и
СМБ-Sales команды (50K+ B2B-фокусированных команд). Каждая вертикаль
получает свой Master-Agent + набор специализированных ролей поверх
горизонтального productivity-core preset. Психографика: возраст 28-42,
техническая грамотность средняя-выше среднего, готовность платить
30 000–80 000 ₽/мес за инструмент, экономящий 10+ часов в неделю.
Покупательский путь: trial (бесплатные 50 T-credits) → upgrade на
RU-Pro подписку через ЮKassa → upsell в vertical pack через 4-6 недель.
""",
    """\
## 3. Продуктовое позиционирование

«Универсальная команда AI-ассистентов для СМБ в РФ. Запусти команду
из 4 ролей за 60 секунд, без подписки на ChatGPT и без VPN. Когда
команда вырастает — добавь вертикальный шаблон для маркетинга,
Telegram, продаж или бухгалтерии». Ключевые differentiators: (1) RU-first
LLM-стек — DeepSeek primary + YandexGPT + GigaChat failover + BYOK для
OpenAI/Anthropic при необходимости; (2) team-first UX — пользователь
взаимодействует с Coordinator, не с отдельными агентами, что снижает
когнитивную нагрузку и совпадает с ментальной моделью «нанять
команду»; (3) vertical depth — Master-Agent layer и 5 готовых шаблонов
позволяют sell-up из горизонтального preset'а в domain-heavy сценарии
без миграции данных или re-onboarding'a. Цена: 2 990 ₽/мес horizontal,
+1 990 ₽/мес за vertical pack — на 40% дешевле ChatGPT Team при сравнимой
производительности на RU-задачах.
""",
    """\
## 4. Go-to-market стратегия

Wave 0 (до 2026-06-09): internal demo + private beta из 10 founders'
кругa. Wave 1 (2026-07-21): pre-alpha с 10-15 friends, фокус на 3
вертикалях (Marketing + Telegram + WB), Telegram Business API
интеграция, ЮKassa открыт. Wave 2 (2026-09-22): public beta с
горизонтальным preset'ом, Pixel Department UI, Pyodide WASM для
кода-исполнителей, Mini App в Telegram. Дистрибуция: контент-маркетинг
в Telegram (целевые каналы для агентств, селлеров, фрилансеров),
inбоунд через SEO на запросы «AI-команда для маркетинг-агентства»,
«chatGPT альтернатива для России», «AI-ассистент для WB-селлера».
Партнёрки — Маркетинг-агентства закрывают деньги-в-руки кейсы и
приводят клиентов на vertical pack через affiliate-программу
(20% revenue share первые 12 месяцев). Founder-led sales в первые 6
месяцев — личные демо для 100+ профильных компаний.
""",
    """\
## 5. Метрики успеха и риски

Wave 0 success metric — internal demo passed: команда producivity-core
прогоняет сценарий «Market & content brief» end-to-end за ≤120 секунд
с total cost ≤30¢ и 3 артефактами (brief.md ≥1500 слов, competitive-matrix.md
с 5×4 таблицей, content-plan.md из 10 постов). Wave 1 success — 10
оплативших клиентов через ЮKassa, NPS ≥40 на pre-alpha cohort.
Wave 2 success — 100 активных команд, monthly revenue ≥500K ₽,
CAC payback ≤4 месяца. Ключевые риски: (R-04) runaway-cost на multi-agent
LLM-инфраструктуре митигируется через max-depth=5 и per-task cost cap
50 T-credits; (R-08) регуляторные изменения по ФЗ-152 митигируются
через раннюю РКН-регистрацию и аудит-trail на каждую операцию с ПДн;
(R-11) retention-риск — vertical pack должен дать измеримый ROI в
течение 30 дней или цикл отписки запустится; митигация — onboarding
с pre-loaded задачами и weekly success-review email-cadence; (R-12)
scope-creep на vertical templates митигируется через Master-Agent layer,
позволяющий пользователю настраивать без code-changes на стороне платформы.
""",
    """\
## 6. Технологический стек и инфраструктура

Backend на Python 3.12 + FastAPI + Pydantic-AI как runtime для агентов.
PostgreSQL 16 с pgvector для долговременной памяти (cell-scoped HNSW
индексы), Redis 7 для rate-limit + pub/sub + JWT blacklist, Dramatiq
для отложенных задач. Frontend — Vite 6 + React 19 + TanStack Router +
Tailwind v4 + shadcn/ui компоненты, без CSS-in-JS. Все вычисления для
аналитического агента — Pyodide WASM в браузере, что даёт zero-server-cost
для тяжёлых расчётов и дополнительный compliance-bonus (numerical data
никогда не покидает клиента). Хостинг — Yandex Cloud ru-central-1 с
полным локированием ПДн в РФ. LLM-провайдеры — DeepSeek V3/R1 как primary
(самый дешёвый на token-cost), YandexGPT и GigaChat как secondary failover
для RU-natural language nuance, BYOK через KMS envelope encryption для
clients, которые хотят свои OpenAI/Anthropic ключи. Custom JWT auth
с argon2-cffi password hashing и refresh-token rotation per OWASP
рекомендациям. Все межсервисные границы — bounded contexts с RLS-policies
в PostgreSQL и FORCE-RLS на всех таблицах с пользовательскими данными.
""",
    """\
## 7. Ценообразование и unit-economics

Базовый тариф horizontal preset — 2 990 ₽/мес включает 500 T-credits
(approx 5M токенов через DeepSeek primary), полную команду из 4 ролей,
неограниченное число задач, RLS-изоляцию, all-RU-cloud размещение.
Vertical pack — +1 990 ₽/мес за один из 5 шаблонов (Marketing, Telegram,
WB, Бухгалтерия, Sales), включает Master-Agent + domain-knowledge base
+ vertical-specific connectors через MCP. BYOK тариф — 990 ₽/мес flat
(только инфра + storage), пользователь приносит свои OpenAI/Anthropic
ключи. Unit economics на horizontal-only тарифе: COGS ~600 ₽/мес
(LLM tokens 400 ₽ + infra 150 ₽ + payment processing 50 ₽), gross
margin 80%. На vertical pack добавляется ~300 ₽/мес COGS на additional
LLM calls для Master-Agent, gross margin сохраняется на уровне 78%.
CAC: ожидание 1 500-3 000 ₽ на клиента через performance-marketing в
Telegram Ads + контент-маркетинг, payback в 1-2 месяца на base subscription,
сокращается до 3-4 недель при upsell на vertical pack. LTV: при среднем
сроке жизни 14 месяцев — 41 860 ₽ на horizontal-only, 69 720 ₽ при
upsell, LTV/CAC от 14× до 47× в зависимости от микс.
""",
    """\
## 8. Команда и founder-fit

Founder с 8+ лет опыта в продуктовой разработке для русскоязычного
B2B-сегмента, технический бэкграунд (Python, FastAPI, distributed systems),
прошедшие проекты — продукты с MAU 50K-500K на стороне СМБ. Operational
mode на Wave 0 — solo founder + 11 AI-моделей-агентов (ZK Steward,
Backend Architect, Senior Project Manager, Code Reviewer, Security
Engineer, Test Results Analyzer, Compliance Auditor, Anthropologist,
Narratologist, Geographer, Historian) под управлением SPARC-методологии.
Это даёт уникальное cost-structure преимущество: первые 12 месяцев
zero-headcount-cost, runway растягивается на 3× по сравнению с
конвенциональным стартапом с командой из 4-6 человек, и каждый AI-агент
оптимизирован под свой role-prompt + golden-dataset, что даёт consistency,
недоступную человеческим командам с rotation. Wave 1+ — найм 1-2
профильных людей (sales + customer success) после product-market-fit
сигналов с pre-alpha cohort. Wave 2+ — полная engineering команда из
3-4 человек при revenue ≥1.5M ₽/мес.
""",
]

_BRIEF_CONCLUSION = """\
## Заключение

Окно возможностей открыто в Q2-Q3 2026: западные игроки не имеют
RU-compliance и не интегрированы с RU-стеком, локальные игроки
(YandexGPT, GigaChat) не имеют агентского runtime и multi-agent
координации, а DIY-решения требуют технической экспертизы, недоступной
типичному SMB-founder'у. Профики занимает середину этой матрицы:
управляемая платформа с RU-compliance, готовыми вертикалями и
ценой на 40% ниже зарубежных аналогов. Wave 0 internal demo —
первая публичная проверка тезиса; Wave 1 pre-alpha с 10-15 friends —
первая внешняя проверка product-market-fit на RU-сегменте.

## Следующие шаги до публичного запуска

В горизонте ближайших 60 дней: завершение Wave 0 (internal demo passed
к 2026-06-09), открытие ЮKassa и юридического лица под оператора ПДн,
финализация бренда и domain (oriion.app + профики.online как vertical entry),
запуск 3 каналов привлечения первых 100 leads (Telegram Ads на агентские
каналы, гостевые публикации в каналах роста экспертизы, SEO-кампания
на 50 ключевых запросов). В горизонте 90-120 дней — pre-alpha с 10-15
бойцов из founder-circle, итерации по role-prompt-hardening на основе
real-world replicate-failures, тонкая настройка vertical Master-Agent
для Marketing-agency как первой публичной вертикали. Wave 1 закроется
с 10 платящими клиентами через ЮKassa, NPS ≥40, и подтверждённым LTV/CAC
≥10× на первой когорте — после этого включается Wave 2 публичный beta
и параллельный найм sales + customer success специалистов.
"""

_WRITER_BRIEF_AND_PLAN = (
    _BRIEF_INTRO
    + "\n".join(_BRIEF_SECTIONS)
    + _BRIEF_CONCLUSION
    + """

# Контент-план на первый месяц (10 постов)

1. **«Запустили AI-команду для российского SMB. Без VPN, с поддержкой ФЗ-152»** — anchor announcement, RU-stack value prop, ссылка на trial.
2. **«Почему ChatGPT Team не работает для российских агентств: 5 проблем»** — competitive teardown, мостик в ваш продукт.
3. **«Как Coordinator + 3 специалиста закрывают market brief за 2 минуты»** — demo video, productivity-core scenario.
4. **«Сколько стоит AI-команда в рублях? Считаем T-credits для маркетинг-агентства»** — pricing transparency, ROI math.
5. **«Vertical templates: что внутри Master-Agent для WB-селлеров»** — deep-dive в самый громкий vertical.
6. **«5 ошибок при найме первого AI-ассистента (и как их избежать с командой)»** — educational, team-first UX positioning.
7. **«BYOK для параноиков: как принести свой OpenAI-ключ и не зависеть от платформы»** — trust-signal для технических founders.
8. **«MCP-протокол на простом языке: чем мы отличаемся от плагинов ChatGPT»** — техническое отличие, для devtool-аудитории.
9. **«Сравнительная таблица: Профики vs ChatGPT Team vs YandexGPT Team»** — feature parity matrix, sales enablement.
10. **«Что дальше: roadmap до Q4 2026 и как клиенты влияют на приоритеты»** — community trust, founder voice.
"""
)


# ── Analyst canned output ────────────────────────────────────────────────
_ANALYST_OUTPUT = """\
# Positioning & sizing analysis

## TAM/SAM/SOM (Wave 0 horizontal preset)

- **TAM** (всё AI-инструментарий для РФ-СМБ): $480M к концу 2025, CAGR 42%
  (Statista 2025; диапазон оценок $400-560M в зависимости от учёта BYOK
  vs только managed-платформ).
- **SAM** (managed AI-команды для 1-10-человечных команд): ~$120M
  (25% TAM, фильтр на team-collaboration use-cases vs single-user
  productivity).
- **SOM** Wave 0+1 (до 2026-Q3): ~$2.4M annualised, при 1 000 платящих
  команд × 200$/мес средний чек.

## Конкурентное позиционирование

Двумерная сетка «locality × team-readiness»:

* Quadrant «global single-user»: ChatGPT, Claude — высокая capability,
  низкая RU-locality, без team-runtime.
* Quadrant «RU single-user»: YandexGPT, GigaChat — средняя capability,
  высокая locality, без team-runtime.
* Quadrant «global team»: ChatGPT Team, Claude Team — высокая capability,
  низкая locality, есть team-features (но не agent-team в нашем смысле).
* **Quadrant «RU team» (наш)**: Профики — единственный игрок с
  agent-team + RU-locality + RU-billing + ФЗ-152.

## Допущения и ограничения

* TAM-оценка чувствительна к курсу USD/RUB (предполагаем диапазон 90-110 ₽/$).
* SOM зависит от скорости adoption — диапазон от $1.2M (медленный)
  до $4.8M (быстрый) к Q3 2026.
* LLM-only Wave 0 — без Pyodide, аналитика на численных выкладках имеет
  ограниченную точность; capability gap callout для Pyodide W2.

## Источники

* Statista 2025 — Russia AI SMB market sizing.
* RBK 2026-Q1 — Adoption survey.
* TAdviser 2026-04 — Barrier analysis.
"""


# ── Coordinator canned output ────────────────────────────────────────────
# AC-W1-16b plan-then-execute: ONE fenced-JSON CoordinatorOutput plan. The
# Coordinator emits the whole delegation_plan in a single completion (no more
# decompose-then-synthesize two-call shape); PlanExecutingCoordinator executes
# it. artifact_type travels IN the plan (AC-W1-24), not a code-side slug map.
_COORDINATOR_PLAN_OBJ = {
    "summary": "Декомпозиция «Market & content brief»: research → analyst → writer.",
    "delegation_plan": [
        {
            "step": 1,
            "agent": "researcher",
            "goal": (
                "Собери конкурентную матрицу ≥5×4 (Игрок | Сегмент | Сильная сторона | "
                "Слабая сторона) и 3 источника по рынку AI-инструментов для СМБ в РФ."
            ),
            "status": "planned",
            "artifact_type": "matrix",
        },
        {
            "step": 2,
            "agent": "analyst",
            "goal": (
                "На основе исследования дай TAM/SAM/SOM с диапазонами и позиционную "
                "сетку locality × team-readiness."
            ),
            "status": "planned",
            "artifact_type": "analysis",
            "depends_on": [1],
        },
        {
            "step": 3,
            "agent": "writer",
            "goal": (
                "Напиши market brief ≥1500 слов на русском и контент-план ровно на 10 "
                "постов в формате '### Пост N — <канал> — <день>'."
            ),
            "status": "planned",
            "artifact_type": "brief",
            "depends_on": [2],
        },
    ],
    "confidence": "high",
}
_COORDINATOR_PLAN = (
    "```json\n" + json.dumps(_COORDINATOR_PLAN_OBJ, ensure_ascii=False, indent=2) + "\n```"
)


def _make_response(text: str, *, in_tokens: int = 150, out_tokens: int = 600) -> ModelResponse:
    return ModelResponse(
        parts=[TextPart(content=text)],
        usage=RequestUsage(
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cache_read_tokens=0,
            details={},
        ),
        model_name="oriion-llm-gateway-fake/canned",
        timestamp=datetime.now(UTC),
        finish_reason="stop",
        provider_name="canned",
    )


# Public registry: (role_key, scenario_id) → list of ModelResponse.
RESPONSES: dict[tuple[str, str], list[ModelResponse]] = {
    ("coordinator", SCENARIO_ID): [_make_response(_COORDINATOR_PLAN, out_tokens=300)],
    ("researcher", SCENARIO_ID): [_make_response(_RESEARCHER_OUTPUT, out_tokens=550)],
    ("writer", SCENARIO_ID): [_make_response(_WRITER_BRIEF_AND_PLAN, out_tokens=2200)],
    ("analyst", SCENARIO_ID): [_make_response(_ANALYST_OUTPUT, out_tokens=480)],
}


# Convenience accessors used by tests/assertions.
def writer_brief_word_count() -> int:
    """Word count of the canned brief (used by AC9 assertions)."""
    return len(_WRITER_BRIEF_AND_PLAN.split())


def researcher_matrix_row_count() -> int:
    """Count of competitive-matrix data rows (excluding header + separator)."""
    matrix_rows = [
        line
        for line in _RESEARCHER_OUTPUT.splitlines()
        if line.startswith("|") and "---" not in line
    ]
    # Subtract 1 for header row.
    return max(0, len(matrix_rows) - 1)


def writer_content_plan_post_count() -> int:
    """Count of numbered posts in the content-plan section."""
    import re

    plan_section = _WRITER_BRIEF_AND_PLAN.split("Контент-план на первый месяц")[1]
    return len(re.findall(r"^\d+\.\s+\*\*", plan_section, flags=re.MULTILINE))
