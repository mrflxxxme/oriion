"""Domain services for llm_gateway.

Each module owns one slice of behaviour:
    kms_provider     — encrypt/decrypt for BYOK keys
    pricing_service  — Decimal pricing table + cost computation (USD + RUB)
    billing_service  — atomic 3-currency write (llm_usage_log + credit_transactions)
    byok_service     — BYOK CRUD + fingerprint + cloudevent emission
    router_service   — LLMRouter (provider selection + failover chain)
    health_service   — health-check + state-transition emission
"""
