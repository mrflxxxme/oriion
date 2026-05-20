"""Seed data for agents bounded context.

Idempotent seeders that INSERT on first call and no-op on subsequent calls
via natural-key conflict checks. Wave 0 ships only the horizontal
`productivity-core` preset; vertical packs land in Wave 1+.
"""
