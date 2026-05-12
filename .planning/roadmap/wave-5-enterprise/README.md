# Wave 5+ — Enterprise & v2 (12+ месяцев)

> Это outline horizon, не detailed plan. Phase-spec'ы появятся после Wave 4 retro и переоценки приоритетов.

## Цель волны

**Enterprise-ready + v2-функциональность.** On-premise deployments, hardware-isolation sandbox, self-hosted LLM на GPU, открытый маркетплейс ролей, episodic memory, видеоконференции.

## Метрика успеха (Целевая)

- 5000+ платящих команд
- MRR ≥50 млн ₽
- 5+ enterprise-клиентов с on-premise/dedicated
- Открытый маркетплейс: 100+ UGC ролей
- 99.95% SLA для enterprise
- 1-я international экспансия (СНГ или дружественные юрисдикции)

## Scope outline

См. [PHASES.md](./PHASES.md). Каждая фаза станет детальной по мере приближения.

### Phase candidates

| ID | Slug | Что включает |
|---|---|---|
| 05.1 | on-premise-helm | Полный Helm-чарт для on-premise, документация, sales-process |
| 05.2 | firecracker-sandbox | Миграция gVisor → Firecracker microVMs |
| 05.3 | self-hosted-gpu | bge-m3 / multilingual-e5 на собственных GPU, замена YandexGPT Embeddings |
| 05.4 | open-weight-models | Qwen / T-Pro / DeepSeek self-hosted для частичной замены международного стека |
| 05.5 | episodic-memory | LangMem-style эпизодическая память + protections от false memories |
| 05.6 | open-marketplace | Открытый UGC-маркетплейс ролей с модерацией, peer-review, ratings |
| 05.7 | video-conferencing | Интеграция с видеосвязью (Yandex Telemost, Kontur Talk) для агентов с voice |
| 05.8 | iso-27001-soc2 | Сертификация для enterprise contracts |
| 05.9 | fstec-cert | ФСТЭК-сертификация для госсектора (опц., после первого gov-клиента) |
| 05.10 | annual-conference | Ежегодная конференция (онлайн → офлайн) |
| 05.11 | international-expansion | Первый рынок СНГ (Казахстан/Беларусь) или дружественной юрисдикции |

## Risks specific

- **R-08:** ФСТЭК-сертификация — 6-12 мес процедура, 3-10 млн ₽; делать только при наличии gov-клиента
- **R-12:** Высокий риск scope creep — жёсткий ICE-фильтр + kill criteria
- **Open-marketplace UGC:** security/quality risk → строгая модерация

## Что меняется в команде

- +Sales/BizDev senior (enterprise sales cycle)
- +Compliance officer / DPO
- +ML/MLOps engineer (для self-hosted GPU)
- +Customer Success leadership (управление командой CS)
- +International growth lead

## Notes for AI-agents

- Этот файл — outline, не actionable spec. Phase-файлы под Wave 5+ создаются перед началом каждой фазы (по результатам Wave 4 retro).
- Все Wave 5+ ставки имеют kill criteria (см. risks/REGISTER.md).
