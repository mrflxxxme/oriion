# PLACEHOLDERS — Реестр TBD-значений

> **Single source of truth для всех TBD identifier'ов.** AI-агенты используют эти token'ы в коде/конфигах когда конкретное значение ещё не известно (зависит от founder-decision из open-questions).
>
> **Правила использования:**
> 1. **Никогда не выдумывай** реальное значение для TBD-token. Цитируй placeholder.
> 2. **В коде** используй placeholder как литерал: `TBD_DOMAIN`, `TBD_OOO_INN`, и т.д. Это позволит легко grep'нуть позже.
> 3. **В config-файлах** используй ENV-var с suffix `_TBD`: `BRAND_DOMAIN_TBD=tbd-brand.ru`. Перед prod деплоем — заменить.
> 4. **При замене реального значения** — обновить эту таблицу и поставить ✅ в Status.
> 5. **При обнаружении нового TBD** — добавить сюда + cross-ref на OQ.

## Status legend

- ⏳ — placeholder, ждёт решения
- ✅ — реальное значение заполнено
- 🚫 — отменено, не нужно для проекта

## Юр.лицо (зависит от OQ-02)

| Token | Назначение | OQ | Status | Реальное значение |
|---|---|---|---|---|
| `TBD_OOO_NAME` | Название юр.лица (ООО «...» или ИП ФИО) | OQ-02 | ⏳ | — |
| `TBD_OOO_INN` | ИНН (10 или 12 цифр) | OQ-02 | ⏳ | — |
| `TBD_OOO_KPP` | КПП | OQ-02 | ⏳ | — |
| `TBD_OOO_OGRN` | ОГРН/ОГРНИП | OQ-02 | ⏳ | — |
| `TBD_OOO_LEGAL_ADDRESS` | Юр.адрес | OQ-02 | ⏳ | — |
| `TBD_OOO_BANK_ACCOUNT` | Расчётный счёт | OQ-02 | ⏳ | — |
| `TBD_OOO_BANK_NAME` | Название банка | OQ-02 | ⏳ | — |
| `TBD_OOO_BANK_BIK` | БИК банка | OQ-02 | ⏳ | — |
| `TBD_OOO_CEO_NAME` | ФИО директора / ИП | OQ-02 | ⏳ | — |
| `TBD_OOO_CEO_PHONE` | Контактный телефон директора | OQ-02 | ⏳ | — |
| `TBD_TAX_REGIME` | УСН-6% / УСН-15% / ОСН | OQ-02 | ⏳ | — |

## РКН-уведомление (OQ-04)

| Token | Назначение | Status |
|---|---|---|
| `TBD_RKN_NOTIFICATION_DATE` | Дата подачи уведомления оператора ПДн | ⏳ |
| `TBD_RKN_OPERATOR_ID` | Номер в реестре операторов ПДн | ⏳ |

## Брендинг и домен (OQ-09)

| Token | Назначение | Status | Note |
|---|---|---|---|
| `TBD_BRAND_NAME` | Бренд-имя продукта | ⏳ | для UI, marketing copy |
| `TBD_BRAND_DOMAIN` | Основной домен (например, foo.ru) | ⏳ | для production |
| `TBD_BRAND_DOMAIN_STAGING` | Staging-домен (например, staging.foo.ru) | ⏳ | для test environment |
| `TBD_BRAND_LOGO_URL` | URL логотипа в S3 | ⏳ | для emails, OG-image |
| `TBD_TRADEMARK_NUMBER` | Номер товарного знака Роспатент | OQ-05 ⏳ | для оферты, copyright |

## Yandex Cloud (закрыто OQ-10, но identifier'ы зависят от регистрации)

| Token | Назначение | Status |
|---|---|---|
| `TBD_YC_ORG_ID` | Yandex Cloud Organization ID | ⏳ (создать) |
| `TBD_YC_FOLDER_ID_DEV` | Folder ID для dev environment | ⏳ |
| `TBD_YC_FOLDER_ID_STAGING` | Folder ID для staging environment | ⏳ |
| `TBD_YC_FOLDER_ID_PROD` | Folder ID для production | ⏳ |
| `TBD_YC_SERVICE_ACCOUNT_DEPLOY` | Service Account для CI/CD deploy | ⏳ |
| `TBD_YC_OBJECT_STORAGE_BUCKET` | S3 bucket name (например, teamly-ru-prod) | ⏳ |
| `TBD_YC_OBJECT_STORAGE_BUCKET_STAGING` | Same для staging | ⏳ |
| `TBD_YC_LOCKBOX_FOLDER_ID` | Folder для secrets | ⏳ |
| `TBD_YC_DATABASE_HOST` | Managed PostgreSQL hostname | ⏳ |
| `TBD_YC_DATABASE_PORT` | Managed PostgreSQL port | ✅ (default 6432 для connection-pooler) |
| `TBD_YC_REDIS_HOST` | Managed Redis hostname | ⏳ |
| `TBD_YC_CDN_RESOURCE_ID` | Cloud CDN resource | ⏳ (Wave 2+) |

## GitHub + GitLab (OQ-11 закрыто, identifier'ы зависят от регистрации)

| Token | Назначение | Status |
|---|---|---|
| `TBD_GITHUB_ORG` | GitHub organization name | ⏳ |
| `TBD_GITHUB_REPO` | Main repo name (например, teamly-ru) | ⏳ |
| `TBD_GITLAB_SELFHOST_URL` | URL self-hosted GitLab mirror | ⏳ deferred Wave 1+ per Phase 00.1 trim (Session-2026-05-17) |
| `TBD_GITLAB_REPO` | Mirror repo URL | ⏳ deferred Wave 1+ |

## ЮKassa (OQ-19)

| Token | Назначение | Status |
|---|---|---|
| `TBD_YUKASSA_SHOP_ID` | ShopId в ЮKassa | ⏳ |
| `TBD_YUKASSA_SECRET_KEY` | Secret API key (в Lockbox) | ⏳ |
| `TBD_YUKASSA_WEBHOOK_SECRET` | Secret для webhook signature verification | ⏳ |
| `TBD_YUKASSA_RETURN_URL` | URL возврата после оплаты | ⏳ |

## LLM-провайдеры (managed keys платформы)

| Token | Назначение | Status | Note |
|---|---|---|---|
| `TBD_DEEPSEEK_API_KEY` | DeepSeek managed key (для managed-tier) | ⏳ | Зарегистрироваться на api.deepseek.com |
| `TBD_YANDEX_GPT_API_KEY` | YandexGPT API key | ⏳ | Через Yandex Cloud SA |
| `TBD_YANDEX_GPT_CATALOG_ID` | Yandex Cloud Catalog ID | ⏳ | = `TBD_YC_FOLDER_ID_PROD` обычно |
| `TBD_GIGACHAT_AUTH_KEY` | GigaChat auth key (Сбер) | ⏳ | developers.sber.ru/gigachat |
| `TBD_BRAVE_SEARCH_API_KEY` | Brave Search API key | ⏳ | для web_search built-in (mcp/tools/web_search.py) |
| `TBD_YANDEX_SEARCH_API_KEY` | Yandex Search API key | ⏳ | альтернативный backend для web_search built-in (РФ-friendly) |
| `TBD_EXA_API_KEY` | Exa neural search API key | ⏳ (опц., Wave 2+) | |

## BYOK + KMS (Phase 00.4 — LLM Gateway encryption)

| Token | Назначение | Status | Note |
|---|---|---|---|
| `TBD_BYOK_MASTER_KEY_B64` | Master AES-256 key (32-byte base64) для `LocalAESKMS` (Wave 0 dev/test) | ⏳ | Генерится локально: `openssl rand -base64 32`. NEVER в репо, только `.env`. Phase 00.6 swap на Yandex KMS — этот placeholder retire'ится. |
| `TBD_YANDEX_CLOUD_KMS_KEY_ID` | Yandex Cloud KMS master key ID для `YandexKMS` impl (Phase 00.6+) | ⏳ | Создаётся в Yandex Cloud Console → KMS → New key. Format: `abjXXXXXXXXXXXX`. |
| `TBD_FX_RATE_USD_TO_RUB_OVERRIDE` | FX rate override для тестов / dev | ⏳ | Default `100.0` в `.env.example`. Wave 1+ заменяется live CBR feed. |

## Email (OQ-28 закрыто, identifier'ы зависят от настройки)

| Token | Назначение | Status |
|---|---|---|
| `TBD_SMTP_HOST` | SMTP host | ✅ (smtp.yandex.ru) |
| `TBD_SMTP_PORT` | SMTP port | ✅ (587 TLS) |
| `TBD_SMTP_USER` | SMTP login (адрес типа noreply@TBD_BRAND_DOMAIN) | ⏳ (зависит от OQ-09 + Yandex 360 setup) |
| `TBD_SMTP_PASSWORD` | App-password для SMTP | ⏳ (в Lockbox) |
| `TBD_NOREPLY_EMAIL` | From-address для transactional emails | ⏳ |
| `TBD_SUPPORT_EMAIL` | Support inbox | ⏳ |

## Уведомления и интеграции

| Token | Назначение | Status |
|---|---|---|
| `TBD_TEAM_TELEGRAM_BOT_TOKEN` | Bot token для нашего official-бота (W3) | ⏳ |
| `TBD_TELEGRAM_NOTIFICATION_BOT_TOKEN` | Bot token для team-нотификаций (alerts) | ⏳ |
| `TBD_YANDEX_TRACKER_ORG_ID` | Yandex Tracker organization ID | ⏳ |
| `TBD_YANDEX_TRACKER_QUEUE_KEY` | Default queue key | ⏳ (e.g. CUSTDISC) |

## Observability

| Token | Назначение | Status |
|---|---|---|
| `TBD_SENTRY_DSN` | Sentry DSN для error tracking | ⏳ (self-hosted в Wave 0.6) |
| `TBD_GRAFANA_ADMIN_PASSWORD` | Grafana admin password | ⏳ (в Lockbox) |

## Команда (solo founder + 11 AI per P-INIT-5)

> Per [GRILL DECISION-3](./decisions/ADR-028-policies-registry.md#decision-3) + [P-INIT-5](./decisions/ADR-028-policies-registry.md#policies-canonical-home): team = 1 founder + 11 persistent Opus AI-агентов. Hire placeholders for Tech Lead / Senior Backend / Senior Frontend / DevOps closed как `🚫 N/A` (OQ-13/14/15 закрыты per P-INIT-5).

| Token | Назначение | Status |
|---|---|---|
| `TBD_TECH_LEAD_NAME` | Имя Tech Lead | 🚫 N/A: solo + AI per P-INIT-5 (OQ-13 closed) |
| `TBD_TECH_LEAD_EMAIL` | Email Tech Lead | 🚫 N/A: solo + AI per P-INIT-5 (OQ-13 closed) |
| `TBD_TECH_LEAD_TELEGRAM` | Telegram Tech Lead | 🚫 N/A: solo + AI per P-INIT-5 (OQ-13 closed) |
| `TBD_SENIOR_BACKEND_NAME` | Имя Senior Backend | 🚫 N/A: backend-implementer AI role per P-INIT-5 (OQ-14 closed) |
| `TBD_SENIOR_FRONTEND_NAME` | Имя Senior Frontend (Wave 1+) | 🚫 N/A: frontend-implementer AI role per P-INIT-5 (OQ-15 closed) |
| `TBD_DEVOPS_NAME` | Имя DevOps (0.5 FTE) | 🚫 N/A: devops-implementer non-persistent AI role per P-INIT-5 (OQ-14 closed) |
| `TBD_FOUNDER_NAME` | Имя founder | ✅ КИРИЛЛ У. (uklonskiy.k@gmail.com) |
| `TBD_DESIGNER_CONTACT` | Контакт freelance pixel-artist (Wave 2) | OQ-25 ⏳ |
| `TBD_LAWYER_CONTACT` | Юрист (Wave 1+) | OQ-03 ⏳ |
| `TBD_ACCOUNTANT_CONTACT` | Бухгалтер (для ЮKassa, Wave 1) | OQ-19 ⏳ |

## Customers (OQ-22)

| Token | Назначение | Status |
|---|---|---|
| `TBD_FRIENDS_LIST_GENERIC_SMB` | Список friends generic SMB / personal-users для pre-alpha Wave 1 (horizontal `productivity-core` entry) | ⏳ |
| `TBD_FRIENDS_LIST_MARKETING_AGENCIES` | Список friends маркетинг-агентств — vertical Wave 1 | ⏳ |
| `TBD_FRIENDS_LIST_TG_CREATORS` | Список friends Telegram-крейторов — vertical Wave 1 | ⏳ |
| `TBD_FRIENDS_LIST_WB_SELLERS` | Список friends WB-Селлеров — vertical **Wave 2** (graduated W0→W2 per Session-2026-05-15) | ⏳ |
| `TBD_FRIENDS_LIST_ACCOUNTING` | Список friends ИП-Бухгалтерии — vertical **Wave 3** (graduated W2→W3) | ⏳ |
| `TBD_FRIENDS_LIST_SMB_SALES` | Список friends СМБ-Sales — vertical **Wave 3** (graduated W2→W3) | ⏳ |

## Финансы (project-scope only)

> Founder-personal финансовые placeholders (burn / runway / funding source) **удалены per Session-2026-05-15** — out-of-scope project docs. AI dev cost caps живут в `.claude/agents/_shared/cost-budget.yaml` (не placeholder, конкретные значения). Любые финансовые tokens в этом разделе должны касаться billing infrastructure / pricing tariffs / contractual amounts (project-facing), не personal capital management.

_(empty — добавлять project-facing financial tokens по мере появления Wave 1+ billing decisions)_

## Юр.документы (зависят от OQ-03, OQ-04)

| Token | Назначение | Status |
|---|---|---|
| `TBD_PRIVACY_POLICY_VERSION` | Версия Privacy Policy | ⏳ |
| `TBD_PRIVACY_POLICY_URL` | URL Privacy Policy | ⏳ (после OQ-03 юрист) |
| `TBD_TOS_VERSION` | Версия оферты | ⏳ |
| `TBD_TOS_URL` | URL оферты | ⏳ |
| `TBD_PDN_CONSENT_TEXT_URL` | Текст согласия на обработку ПДн | ⏳ |
| `TBD_CROSS_BORDER_CONSENT_TEXT_URL` | Согласие на трансгранич. передачу (для Western LLM) | ⏳ (Wave 2+) |

## Marketing (Wave 2+, OQ-21)

| Token | Назначение | Status |
|---|---|---|
| `TBD_TELEGRAM_FOUNDER_CHANNEL` | Founder Telegram-канал URL | ⏳ |
| `TBD_BLOG_URL` | Blog URL (vc.ru / habr / собственный) | ⏳ |
| `TBD_LANDING_DOMAIN` | Marketing landing domain | ⏳ (Wave 2+) |

## Workflow для AI-агентов: что делать при встрече TBD

```
1. AI-агент пишет код / config / phase-file
2. Встречает место, где нужно "реальное значение", которое не закрыто
3. Look up в этом файле — есть TBD_TOKEN?
   ├─ Yes: использовать TBD_TOKEN как литерал в коде/значении
   └─ No: 
      ├─ Это новая TBD-категория → escalate: создать новый TBD_TOKEN + добавить сюда
      └─ Это решаемое значение → решить без TBD (просто реальный default)
4. После использования TBD в коде → grep сменa TBD_TOKEN потом тривиально
```

## Замена TBD на реальные значения (для founder/команды)

```bash
# После того как зарегистрировали ООО:
# 1. Заполнить значения в этом файле (status → ✅)
# 2. В коде: grep -r "TBD_OOO_INN" backend/ frontend/ infra/ — заменить
# 3. В config: обновить ENV-vars (без _TBD suffix)
# 4. Commit: "chore: replace TBD_OOO_* with actual values"
```

