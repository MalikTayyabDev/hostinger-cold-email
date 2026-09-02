# Troubleshooting

## SMTP authentication failed

- Verify `SMTP_USER` and `SMTP_PASSWORD` in `.env`
- Confirm Hostinger mailbox password (not hosting panel password)
- Try port 465 (SSL) or 587 (STARTTLS)

## No emails sending

- Check `DRY_RUN` — set to `false` for live sends
- Campaign must be **Active** (not Draft or Paused)
- Check daily limit on dashboard
- Verify leads are `pending` and not suppressed/bounced/replied

## IMAP / reply detection not working

- Set `DRY_RUN=false` (IMAP is skipped in dry-run)
- Verify `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_HOST`
- Check `logs/app.log` for IMAP errors

## Duplicate leads on import

- Duplicates are blocked per campaign (same normalized email)
- Check import preview for duplicate counts

## Scheduler sends nothing

- Only **active** campaigns send
- Follow-ups require `next_action_at` to have passed
- Daily limit may be reached

## Dashboard won't start

- Port 5000 in use — change `APP_PORT` in `.env`
- Missing dependencies — run `pip install -r requirements.txt`

## Tests

```powershell
pytest -v
```

Tests never send real email (`DRY_RUN=true`).

## Logs

Check `logs/app.log` for structured errors. Passwords are never logged.
