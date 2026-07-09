"""Seed data for agents bounded context.

Idempotent seeders that INSERT on first call and no-op on subsequent calls
via natural-key conflict checks. Wave 0 ships only the horizontal
`productivity-core` preset; vertical packs land in Wave 1+.

Wave-1 vertical packs (Master-Agent layer, ADR-029):
  - ``agency_marketing_ru_v1`` — first Wave-1 vertical (Phase 01.2).
  - ``telegram_creator_v1`` — second Wave-1 vertical (Phase 01.10), adds a
    Master + a vertical-specific ``community-manager`` (Telegram-bot
    connector consumer) on top of the reused horizontal specialists.
"""
