"""iam.services — orchestration + domain primitives.

Order of dependency:
    password_service  →  no peers
    token_service     →  uses Redis (blacklist), no peers
    rate_limit_service →  uses Redis, no peers
    consent_service   →  consent_repository
    email_service     →  EmailSender impls (Console / NoOp / InMemory)
    auth_service      →  composes everything above
"""
