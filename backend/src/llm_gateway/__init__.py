"""LLM Gateway bounded context.

Per ADR-024 the gateway unifies provider routing (DeepSeek primary per ADR-018,
YandexGPT, GigaChat, OpenAI/Anthropic via BYOK), BYOK key custody (AES-256-GCM
via KMSProvider), and per-call usage telemetry with atomic 3-currency write
(cost_usd + cost_rub + fx_rate) per ADR-018 amendment 2026-05-19.

Public entry points live under ``src.llm_gateway.routers`` (FastAPI APIRouter
instances) and ``src.llm_gateway.services`` (domain orchestrators).
"""
