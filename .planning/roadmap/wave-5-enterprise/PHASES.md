# Wave 5+ — Phase Outlines

> Outline-only. Detailed phase-spec'ы создаются перед каждой фазой после Wave 4 retro.

## Phase outlines

### 05.1 On-premise Helm-чарт
- Helm-chart для установки в клиентский Yandex/VK/MTS Cloud / on-prem
- License-server + telemetry opt-in
- Установочный скрипт + documentation
- Sales-process для enterprise (RFP, security audit)

### 05.2 Firecracker microVMs (sandbox)
- Замена gVisor → Firecracker для роли Dev
- Hardware-level isolation
- Cold start <200ms
- Dedicated bare-metal hosts (Yandex Cloud BareMetal или собственные)

### 05.3 Self-hosted GPU + embedding
- Yandex DataSphere GPU или собственные A100
- bge-m3 / multilingual-e5-large на собственной инфре
- Замена YandexGPT Embeddings (стоимость + control)

### 05.4 Open-weight LLM для частичных задач
- Qwen 3 / T-Pro / DeepSeek self-hosted
- Замена части RU-стека на собственный
- Cost reduction на масштабе

### 05.5 Episodic memory
- LangMem-style эпизодическая память
- Защита от false memories (citation требуется, hallucination scoring)
- Per role config: enable/disable
- Migration с current 2-level memory

### 05.6 Open marketplace ролей
- UGC: любой клиент публикует роль
- Модерация (auto + human)
- Peer review + ratings
- Monetization для авторов (premium roles)
- Anti-abuse: спам, copyright violation

### 05.7 Видеосвязь интеграция
- Yandex Telemost / Kontur Talk API
- Agent с voice (whisper + TTS)
- «Виртуальный участник» в conf-call'е

### 05.8 ISO 27001 / SOC 2 Type II
- Подготовка к certification (внешний аудит, ~6 мес процесс)
- Документация SoA, ISMS, BCP/DR
- Стоимость: 2-5 млн ₽

### 05.9 ФСТЭК-сертификация (опц., после gov-клиента)
- 6–12 мес процедура
- Спец.условия: код в РФ, доли, СЗИ-классы
- Триггерится после первого крупного gov-клиента

### 05.10 Annual conference
- Онлайн-конференция (1000+ участников)
- Showcase платящих клиентов
- Partner-награды
- Annoucements (новые features, roadmap)

### 05.11 International expansion
- Первый рынок: СНГ (Казахстан / Беларусь / Узбекистан)
- Localization (kk-KZ / uz-UZ)
- Местные платёжные системы
- Юр.структура

## Priorities (initial — pre-Wave-4-retro)

Высокий приоритет:
- 05.1 (on-premise) — необходимо для enterprise pipeline
- 05.8 (ISO/SOC) — параллельно

Средний:
- 05.2, 05.3, 05.4 — cost optimization
- 05.6 (marketplace) — defensible moat extension

Низкий / условный:
- 05.5 (episodic memory) — после product-market fit
- 05.7 (video) — после feedback
- 05.9 (ФСТЭК) — после gov-клиента
- 05.10, 05.11 — после стабилизации

## Notes for AI-agents

- НЕ создавать phase-files под Wave 5+ заранее. Каждая phase = отдельный мини-проект, спец писать на этапе подготовки к ней.
- Если в текущей работе обнаружено что-то критически важное для Wave 5+ — записать в backlog в [_meta/wave5-backlog.md](../../_meta/wave5-backlog.md) (создать при необходимости).
