"""Artifacts bounded context (ADR-012 / ADR-038, Phase 01.5).

Persistent storage of work products: Yjs CRDT documents (bytea + pycrdt,
REST-only persistence in Wave 1), S3 binary assets (presigned upload against
MinIO / Yandex Object Storage) and citeable ``artifact://`` URLs with stable
immutable versions. Envelope model per ADR-038.
"""
