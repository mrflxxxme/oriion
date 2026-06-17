# Alertmanager secret files (AC-W1-15)

Alertmanager reads notifier credentials from files (never inlined in
`alertmanager.yml`). The deploy workflow materializes these from YC Lockbox into
this directory, which is mounted read-only at `/etc/alertmanager/secrets/` by
`docker-compose.staging.yml`.

| File | Lockbox key | What |
|---|---|---|
| `telegram_bot_token` | `LOCKBOX_ALERT_TELEGRAM_BOT_TOKEN` | BotFather token for the ops alert bot |
| `pagerduty_routing_key` | `LOCKBOX_ALERT_PAGERDUTY_ROUTING_KEY` | PagerDuty Events API v2 integration key |

The non-secret Telegram `chat_id` lives in `alertmanager.yml` (a structural
value, replace the `TBD_ALERT_TELEGRAM_CHAT_ID` per `.planning/PLACEHOLDERS.md`).

The committed files hold the literal `TBD_REPLACE_FROM_LOCKBOX` placeholder so the
stack boots in local validation; replace them (or let the deploy overwrite) before
alerts can actually deliver. Do NOT commit real tokens.
