# Tech Stack — единый источник правды

> Не повторять версии/провайдеров в phase-файлах — ссылаться сюда. При смене версии — обновить здесь.

## Backend

| Слой | MVP (Wave 0–3) | Scale (Wave 4) | Enterprise (Wave 5+) |
|---|---|---|---|
| Language | Python 3.12, strict type hints | Same | + Go для hot-paths при необходимости |
| Framework | FastAPI 0.115+ + uvicorn | Same | Same |
| Agent runtime | **Pydantic-AI** (latest) + наш Team/Role/Coordinator слой + native MCP-support | Same | + Self-hosted open-weight LLMs (Qwen/DeepSeek/T-Pro) |
| ORM | SQLAlchemy 2.x + Alembic | Same | Same |
| Async I/O | asyncio + httpx + asyncpg + redis.asyncio | Same | Same |
| Validation | Pydantic v2 | Same | Same |
| Logging | structlog (JSON) + OpenTelemetry | Same | Same |

## Frontend (Главный SPA)

| Слой | MVP (Wave 0–3) | Scale (Wave 4) |
|---|---|---|
| Build tool | **Vite 6** | Same |
| Language | TypeScript 5.6+ strict | Same |
| Framework | **React 19** | Same |
| Routing | **TanStack Router v1** (file-based, type-safe) | Same |
| Server state | TanStack Query v5 | Same |
| Global state | Zustand | Same |
| Styling | Tailwind v4 + shadcn/ui (copy-paste components) | Same |
| Forms | react-hook-form + zod | Same |
| Animation | Motion (Framer Motion v11+) для UI; CSS keyframes для Pixel | Same |
| 2D rendering | **Native HTML5 Canvas 2D** (ADR-004) | + WebTransport low-latency (опц.) |
| Real-time | WebSocket (native) | + y-redis для cluster |
| API client | orval / openapi-typescript (codegen из FastAPI OpenAPI) | Same |
| Testing | Vitest + Playwright | Same |
| i18n | react-i18next, default ru-RU | + en-US (Wave 5+ international) |

## Code execution (Analyst роль)

| Слой | MVP (Wave 2) | Wave 3+ опционально | Wave 5+ Enterprise |
|---|---|---|---|
| Primary | **Pyodide WASM в браузере** (Web Worker) | Same | Same |
| Pre-loaded packages | pandas, numpy, matplotlib, scipy, sklearn, BeautifulSoup, openpyxl | Same | Same |
| Server-side опция | — | gVisor + Docker sandbox | + Firecracker microVMs |

## Marketing site (отдельный трек, Wave 2+)

| Слой | Wave 2+ |
|---|---|
| Framework | **Astro 5** (static SSG) |
| Content | Markdown / MDX |
| Deployment | Yandex Object Storage + CDN (separate domain) |

## Auth / IAM

| Слой | MVP (Wave 0–1) | Wave 2–3 | Wave 4+ Enterprise |
|---|---|---|---|
| Auth | **Custom JWT** (pyjwt + bcrypt + Redis blacklist) | **Logto** self-hosted | + Keycloak для SAML/AD/SSO |
| 2FA | TOTP (pyotp) Wave 1 | Same | + WebAuthn / passkeys |
| OAuth providers (Wave 1) | Yandex ID, VK ID | + Google (для glob клиентов) | Same |
| Magic-link login | Wave 1 | Same | Same |

## Хранилища

| Слой | MVP | Scale | Enterprise |
|---|---|---|---|
| Основная БД | PostgreSQL 16 + RLS | + read-replicas | + Citus/Patroni шардирование |
| Vector | pgvector (extension) | Qdrant standalone | Same |
| Cache / queues | Redis 7 + Dramatiq | + NATS JetStream если потребуется | Same |
| Object storage | **Yandex Object Storage** (S3-compat) | Same | + BYOK customer S3 |
| Document collab | Yjs + y-websocket (single-node) | + y-redis | Same |

## Инфраструктура и deployment

| Слой | MVP (Wave 0–3) | Scale (Wave 4) | Enterprise (Wave 5+) |
|---|---|---|---|
| Cloud | **Yandex Cloud** (ru-central-1, Москва) | Same | + VK Cloud / Selectel / MTS Cloud / on-premise |
| Deploy | Docker Compose на 1–3 VM + Caddy reverse proxy | Yandex Managed K8s + Helm + ArgoCD | + on-premise Helm-чарт |
| CI/CD | GitHub Actions (через VPN-runner или GitLab fallback) | + ArgoCD GitOps | Same |
| Region | ru-central-1 single | + ru-central-2 (DR) | + customer cloud / on-prem |

## LLM-провайдеры (триконтурный стек)

### Контур 1: China (Premium, прямой API из РФ) — Wave 0+

| Провайдер | SDK | Использование | Модели |
|---|---|---|---|
| **DeepSeek** | openai-python (OpenAI-compatible base_url) | Premium (Coordinator, Researcher, Writer, Analyst) | DeepSeek-V3, DeepSeek-R1 |
| Qwen (опц., Wave 1+) | openai-compatible | Multilingual fallback | Qwen3-Max |

### Контур 2: RU (Managed, прямой API) — Wave 0+

| Провайдер | SDK | Использование | Модели |
|---|---|---|---|
| **YandexGPT** | `yandex-cloud-ml-sdk` | RU-managed + Embeddings | YandexGPT 5 Pro, 5 Lite, Embeddings (text-search-doc/query) |
| **GigaChat (Сбер)** | `gigachat-py` | RU-business alternative | GigaChat Pro, Max |

### Контур 3: Western (Wave 2+, через прокси)

| Провайдер | SDK | Использование |
|---|---|---|
| Anthropic Claude | `anthropic` (base_url override для прокси) | Premium Western (BYOK preferred) |
| OpenAI GPT | `openai` (base_url override) | Premium Western (BYOK preferred) |
| Google Gemini | `google-generativeai` | Multimodal fallback (Wave 3+) |
| OpenRouter | openai-compatible | Multi-provider gateway (Wave 3+) |

### Прокси-кандидаты для Контур 3 (Wave 2+ task)

- vsegpt.ru / ProxyAPI / BotHub / собственный VPS в Армении
- Multi-proxy с health-check (ADR-002)

### BYOK (с Wave 0)

9 провайдеров поддерживается в API Keys UI: `deepseek`, `yandex`, `gigachat`, `openai`, `anthropic`, `google`, `openrouter`, `brave`, `exa`

## Integrations (через MCP-протокол)

### Wave 0: Built-in (без MCP)
- web_search (Brave Search API / Yandex Search)
- read_url (httpx + readability-lxml)

### Wave 1: РФ-killer MCP-серверы (наши)
- `telegram-mcp` (Telegram Bot API)
- `yandex-disk-mcp`
- `imap-smtp-mcp` (Yandex 360 / Mail.ru Pro)

### Wave 2: Vertical-template коннекторы (наши)
- `bitrix24-mcp`
- `amocrm-mcp`
- `wb-partners-mcp`
- `ozon-seller-mcp`
- + Community: `github-mcp`, `notion-mcp`, `slack-mcp`, `gmail-mcp`, `google-drive-mcp`, `google-sheets-mcp`

### Wave 3: Heavy РФ-corp
- `1c-rest-mcp`
- `kontur-elba-mcp`
- `kontur-extern-mcp`
- `tinkoff-business-mcp`

### Wave 4+: Open marketplace + Composio bridge (опц.)

## Платежи и биллинг

| Назначение | Сервис | Заметки |
|---|---|---|
| Приём оплат от РФ | **ЮKassa** (карты + СБП) | Подключение через ООО РФ |
| B2B-счета | Тинькофф Бизнес / Точка | Волна 3+ |
| Оплата зарубежных LLM (Wave 2+) | Карта зарубежного юр.лица (Армения/ОАЭ) | Wave 2+ blocker resolves |

## Безопасность

| Слой | Решение |
|---|---|
| WAF / DDoS | DDoS-Guard (РФ) или Curator (Selectel) |
| CAPTCHA | SmartCaptcha (Yandex Cloud) |
| Secrets | Yandex Cloud Lockbox (managed KMS) |
| SAST | Semgrep + Bandit |
| Dependency scan | pip-audit + npm audit + Snyk free |
| Secrets scan | gitleaks + trufflehog (pre-commit + CI) |
| Container scan | Trivy |
| SBOM | Syft + Grype |
| Backup encryption | envelope encryption + Yandex KMS |

## Observability

| Компонент | MVP (Wave 0-3) | Scale (Wave 4+) |
|---|---|---|
| Traces | OpenTelemetry → Tempo single-node | + Tempo cluster |
| Logs | Loki single-node | + Loki cluster |
| Metrics | Prometheus | VictoriaMetrics |
| Dashboards | Grafana | Grafana |
| Agent traces | Опционально Langfuse self-hosted (Wave 3) | Langfuse cluster |
| Error tracking | Sentry self-hosted | Same |

## Pixel-art pipeline (Wave 2)

| Tool | Назначение |
|---|---|
| **SDXL** / Flux.1-dev | AI-generation baseline (24 archetypes) |
| **Pixel-Art-XL LoRA** | Style transfer для pixel-aesthetic |
| **ComfyUI** | Visual pipeline orchestration |
| **Aseprite** | Manual post-processing, animation frames |
| Yandex DataSphere GPU | Compute для generation |
| Freelance pixel-artist | 5 vertical-героев hand-drawn (FL.ru / Хабр Карьера) |

## Версии и обновления

- Обновление зависимостей: автоматически через Renovate / Dependabot
- Major-версии: PR с ручным ревью, регрессионные тесты обязательны
- Patch security: auto-merge при зелёном CI (см. [conventions.md](./conventions.md) tier-review)

