# Architecture

## Stack

- **Python 3.10+**, Flask, SQLite, python-dotenv
- Hostinger SMTP (port 465 SSL or 587 STARTTLS)
- Hostinger IMAP (port 993) for reply/unsubscribe detection

## Project structure

```
app.py                 Flask factory + entry point
config.py              Environment configuration
scheduler.py           Background sending loop
backup.py              Database backup
manage.py              CLI utilities
database/db.py         Schema, migrations, indexes
services/
  template_service.py  {{variable}} rendering
  email_service.py     SMTP + IMAP
  lead_service.py      Lead CRUD, import/export
  campaign_service.py  Campaigns + sequences
  scheduler_service.py Sending, inbox processing, stats
routes/                Flask blueprints
templates/             Jinja2 UI
static/css/            Styles
tests/                 pytest suite
logs/                  Application logs
backups/               Database backups
```

## Database entities

| Table | Purpose |
|-------|---------|
| campaigns | Campaign name, status, limits |
| campaign_steps | Sequence steps (subject, body, delay) |
| leads | Contact data (normalized email) |
| campaign_leads | Lead ↔ campaign state, sequence progress |
| email_events | Audit log (sent, reply, bounce, etc.) |
| suppressions | Global do-not-email list |
| users | Optional admin auth |

## Send flow

1. Scheduler/manual trigger calls `process_inbox()` then `send_batch()`
2. `eligible_sends()` finds campaign_leads on active campaigns
3. `acquire_send_lock()` prevents duplicate sends on restart
4. Template rendered → SMTP send (or dry-run log)
5. On success: update status, schedule next step, log `sent` event
6. On bounce: mark bounced, add to suppressions

## Idempotency

Send locks (`send_lock_until`) plus eligibility re-check before each send ensure restarts do not double-send.
