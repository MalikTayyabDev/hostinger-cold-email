# Hostinger Cold Email Automation

A self-hosted Python outreach platform for legitimate cold email using Hostinger SMTP/IMAP, Flask, and SQLite.

## Features

- Campaign management with configurable email sequences
- Lead import/export with preview and duplicate detection
- `{{variable}}` personalization with safe fallbacks
- Email preview and test send
- Hostinger SMTP (SSL + STARTTLS) and IMAP reply detection
- Bounce and unsubscribe handling with suppression list
- Daily send limits, randomized delays, dry-run mode
- Optional dashboard authentication
- CSRF protection on POST actions
- Scheduler with idempotent send locking
- Backup script and CLI utilities

## Quick start (Windows)

```powershell
cd hostinger_cold_email_system
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Hostinger credentials
python app.py
```

Open http://127.0.0.1:5000

## Commands

| Command | Purpose |
|---------|---------|
| `python app.py` | Start dashboard |
| `python scheduler.py` | Automatic sending loop (15 min) |
| `python backup.py` | Backup SQLite database |
| `python manage.py stats` | Print stats |
| `python manage.py test-email` | Send SMTP test |
| `python manage.py import leads.csv` | CLI import |
| `pytest` | Run tests |

## Workflow

1. Configure `.env` (see `.env.example`)
2. Set `DRY_RUN=true` and test
3. Create a campaign → edit sequence steps
4. Import leads (CSV preview first)
5. Start campaign
6. Send manually or run `python scheduler.py`
7. Set `DRY_RUN=false` when ready for live sending

## CSV columns

`name`, `first_name`, `last_name`, `company`, `email`, `website`, `industry`, `location`, `custom_line`, `tags`

## Template variables

`{{first_name}}`, `{{last_name}}`, `{{full_name}}`, `{{company}}`, `{{website}}`, `{{industry}}`, `{{location}}`, `{{custom_line}}`, `{{sender_name}}`, `{{unsubscribe_url}}`, `{{unsubscribe_footer}}`, `{{email_footer}}`

## Security

- Bind to `127.0.0.1` by default
- Set `ADMIN_USERNAME` + `ADMIN_PASSWORD` for auth
- Never commit `.env`
- Use `PUBLIC_BASE_URL` with HTTPS for unsubscribe links

## Documentation

- [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md) — **GitHub → Supabase → Vercel → SMTP**
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SETUP_WINDOWS.md](SETUP_WINDOWS.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [PROJECT_AUDIT.md](PROJECT_AUDIT.md)

## Compliance

Use for legitimate, relevant outreach. Respect opt-outs, applicable laws, and provider limits. This tool does not bypass spam filters or abuse controls.
