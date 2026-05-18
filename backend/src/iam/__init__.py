"""iam — Identity & Access Management bounded context.

Per ADR-024 / contracts/iam/. Owns:
  * users (canonical person record)
  * sessions + refresh_tokens (login sessions + OWASP rotation chain)
  * consents (FZ-152 ledger)
  * email_verification_tokens + password_reset_tokens
  * oauth_links (DDL only in Wave 0; code in Wave 1)
"""
