# FOUNDER-RUNWAY — манифест founder-зависимостей

> Единая панель разблокировок per [ADR-040 D7](./decisions/ADR-040-execution-spec-contract.md).
> Всё, что может дать только founder (креды, юр-решения, аккаунты), — здесь, с указанием, какие
> фазы это гейтит. `/autonomy:run` на preflight сверяет очередь с этим файлом: фаза с
> неудовлетворённой зависимостью **паркуется до старта** (RUN-QUEUE `parked` + notify), очередь
> продолжается со следующей независимой фазы.
>
> Секреты передаются ТОЛЬКО через канонический git-ignored `backend/.env` (dev) / Yandex Lockbox
> (staging/prod) — никогда через этот файл, чат или коммиты.

## Активные зависимости

| ID | Зависимость | Гейтит | Как разблокировать | Статус |
|---|---|---|---|---|
| RW-01 | SMTP-креды Yandex 360 (`SMTP_USER`/`SMTP_PASSWORD` + from-адрес) | 01.8-mail live-send (DV-06); pre-alpha launch | Завести ящик → положить креды в канон. `.env` + Lockbox → сказать раннеру «RW-01 ready» | 🔴 waiting |
| RW-02 | OAuth client-креды: Yandex ID + VK ID (регистрация приложений) | 01.8b целиком | Зарегистрировать 2 приложения → client_id/secret в канон. `.env` | 🔴 waiting |
| RW-03 | Telegram bot-token + тестовый канал | 01.10 live-демо (dev-часть 01.10 НЕ гейтит: research-brief, промпты, golden — автономны) | @BotFather → токен в канон. `.env` + создать тест-канал | 🔴 waiting |
| RW-04 | OQ-02 (ООО vs ИП) + OQ-19 (счёт ЮKassa, 5–10 дней) | 01.3b целиком (billing-core НЕ гейтит) | Юр-решение + открытие аккаунта → тест-shop креды | 🔴 waiting (внешний процесс) |
| RW-05 | OQ-32 (consent-UX текст) + OQ-33 (РКН-уведомление update) | 01.11 целиком (feature-flagged) | Founder + юрист: утвердить текст согласия + подать обновление | 🔴 waiting (юрист) |
| RW-06 | Staging cutover-секреты (Telegram/PagerDuty/S3 через Lockbox) | Alerting live-проверка на staging (AC-W1-9/15 boundary) | Заполнить Lockbox-секреты → redeploy staging | 🔴 waiting |
| RW-07 | Founder staging 10× anchor run (гейт wave-0-to-1, DV-08) + 00.8 e2e:live (DV-09) | Формальное закрытие Wave 0 (dev Wave 1 НЕ гейтит — уже идёт) | Прогнать runbook `docs/runbooks/staging-bootstrap.md` + `npm run e2e:live` | 🔴 waiting |
| RW-08 | Funded LLM-ключи в каноне `.env` (DeepSeek + Yandex) | Все live-golden evidence-гейты | Уже в каноне; поддерживать баланс DeepSeek | 🟢 ready |
| RW-09 | Docker-стек up перед `/autonomy:run` | Integration + live-гейты любой фазы | `make dev` перед запуском раннера | 🟢 ready (процедурно) |

## Протокол

1. **Разблокировка:** founder кладёт секрет в канон (`.env`/Lockbox), меняет статус на 🟢 ready (сам или командой раннеру «RW-NN ready»). Раннер при следующем preflight вливает распаркованные фазы в очередь.
2. **Новая зависимость:** любая фаза, обнаружившая founder-зависимость, добавляет RW-строку в том же PR (и ссылается на неё из спеки, DoR пункт 5).
3. **Гейт волны:** зависимости, не разблокированные к гейту волны, — основание перенести гейтед-фазы в следующую волну решением гейта (ADR-040 D4), НЕ основание держать волну открытой.
4. **Связь с OPEN-QUESTIONS:** OQ-строки остаются каноном формулировки вопроса; RW-строки — операционная проекция «что именно положить куда, чтобы раннер поехал».
