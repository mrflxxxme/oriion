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

## Пошаговые инструкции разблокировки

Посадочные места для всех ключей уже добавлены в `.env.example` (блоки SMTP / OAuth / Telegram) — копируйте строку в канонический `backend/.env` и заменяйте `TBD_*` реальным значением. После каждой разблокировки: смените статус в таблице выше на 🟢 (сами или командой раннеру «RW-NN ready»).

### RW-01 — SMTP (≈15 мин)
1. В Яндекс 360 / Яндекс Почте завести ящик вида `no-reply@<домен>` (или использовать существующий).
2. В настройках Яндекс ID ящика: «Пароли приложений» → создать пароль приложения для «Почта (IMAP/SMTP)» — основной пароль аккаунта НЕ подходит.
3. В аккаунте почты включить «Разрешить доступ по SMTP».
4. В `backend/.env`: `SMTP_USER=<ящик>`, `SMTP_PASSWORD=<пароль приложения>`, `SMTP_FROM=<тот же ящик>` (Yandex отклоняет чужой From). Хост/порт/TLS уже предзаполнены (smtp.yandex.ru:465, implicit TLS).
5. Проверка: `cd backend && uv run pytest -m live tests/iam -k smtp` — гасит [DV-06](./DEFERRED-VERIFICATION.md).

### RW-02 — OAuth Yandex ID + VK ID (≈30–45 мин, нужно ДО старта 01.8b, не сейчас)
1. **Yandex ID:** oauth.yandex.ru → «Создать приложение» → платформа «Веб-сервисы», Redirect URI `https://<BRAND_DOMAIN>/api/v1/auth/oauth/yandex/callback` (+ `http://localhost:8000/...` для dev), доступы: логин/email. Получить ClientID + Client secret.
2. **VK ID:** id.vk.com → кабинет разработчика → создать приложение VK ID, тот же паттерн Redirect URI, доступ email. Получить ID + защищённый ключ.
3. Значения → `backend/.env` в блок `*_OAUTH_*` (имена финализируются в 01.8b spec — раннер сам переименует при необходимости).

### RW-03 — Telegram bot-token (≈5 мин; дёшево, держит live-часть второй вертикали)
1. В Telegram → @BotFather → `/newbot` → имя/username → скопировать токен.
2. Создать приватный тестовый канал, добавить бота администратором (право «публиковать сообщения»), узнать chat_id (переслать любой пост в @getidsbot или через `getUpdates`).
3. `backend/.env`: `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_TEST_CHANNEL_ID=...`.

### RW-04 — ЮKassa (внешний процесс, 5–10 рабочих дней; гейтит только 01.3b)
1. Решить OQ-02 (ООО vs ИП) — юр-вопрос, вне компетенции раннера.
2. Подать заявку на yookassa.ru (нужны: реквизиты юрлица/ИП, расчётный счёт, сайт/описание сервиса).
3. После одобрения: включить **тестовый магазин** → `shopId` + секретный ключ теста → в канон при старте 01.3b.

### RW-05 — Consent-UX + РКН (юрист; гейтит только 01.11)
1. Юристу: текст согласия на обработку переписки через Telegram Business API (152-ФЗ) + проверить, требуется ли обновление РКН-уведомления (обработка новой категории данных).
2. По готовности текстов — приложить в `.planning/contracts/` как контракт consent-экрана; раннер отэскалирует финальную формулировку в 01.11 discuss.
3. По запросу могу подготовить драфт consent-текста для проверки юристом.

### RW-06 — Staging cutover-секреты (Lockbox; ≈20 мин)
1. В Yandex Lockbox добавить: Telegram alert-bot token + chat_id (Alertmanager), PagerDuty routing key, S3-креды для Loki-архива (ключи перечислены в `infra/` observability-конфигах / runbook staging-bootstrap).
2. Redeploy staging (`deploy-staging.yml`); проверить тестовым critical-алертом.

### RW-07 — Staging 10× anchor run (≈1–1.5 ч; формально закрывает Wave 0)
1. Прогнать runbook `docs/runbooks/staging-bootstrap.md` (стенд должен быть up).
2. `python -m scripts.demo_market_brief --api-base-url https://staging.oriion.dev/api/v1 --jwt <demo> --cell-id <demo> --runs 10 --output .planning/gates/evidence/wave-0-to-1/ --tolerate-failures 1`.
3. `npm run e2e:live` из `frontend/` против staging (гасит [DV-09](./DEFERRED-VERIFICATION.md)).
4. Скринкаст ≤30 мин + артефакты → `.planning/gates/evidence/wave-0-to-1/` → подписать гейт (гасит DV-08).

## Протокол

1. **Разблокировка:** founder кладёт секрет в канон (`.env`/Lockbox), меняет статус на 🟢 ready (сам или командой раннеру «RW-NN ready»). Раннер при следующем preflight вливает распаркованные фазы в очередь.
2. **Новая зависимость:** любая фаза, обнаружившая founder-зависимость, добавляет RW-строку в том же PR (и ссылается на неё из спеки, DoR пункт 5).
3. **Гейт волны:** зависимости, не разблокированные к гейту волны, — основание перенести гейтед-фазы в следующую волну решением гейта (ADR-040 D4), НЕ основание держать волну открытой.
4. **Связь с OPEN-QUESTIONS:** OQ-строки остаются каноном формулировки вопроса; RW-строки — операционная проекция «что именно положить куда, чтобы раннер поехал».
