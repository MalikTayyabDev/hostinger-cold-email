# Windows Setup

## Prerequisites

- Python 3.10 or newer (`py --version`)
- Hostinger email mailbox with SMTP/IMAP enabled

## Installation

```powershell
cd D:\Desktop\hostinger_cold_email_system\hostinger_cold_email_system
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

## Configure `.env`

Required for live sending:

```env
SMTP_USER=hello@yourdomain.com
SMTP_PASSWORD=your-mailbox-password
FROM_NAME=Your Name
FROM_EMAIL=hello@yourdomain.com
IMAP_USER=hello@yourdomain.com
IMAP_PASSWORD=your-mailbox-password
DRY_RUN=true
```

For SSL (default): `SMTP_PORT=465`, `SMTP_ENCRYPTION=ssl`  
For STARTTLS: `SMTP_PORT=587`, `SMTP_ENCRYPTION=starttls`

## First run

```powershell
python app.py
```

Visit http://127.0.0.1:5000

## Scheduler as background task

Keep a PowerShell window open:

```powershell
.\.venv\Scripts\activate
python scheduler.py
```

Or use Windows Task Scheduler to run `scheduler.py` at login.

## Optional authentication

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
SECRET_KEY=random-hex-string
```

## Backup

```powershell
python backup.py
```

Backups saved to `backups/campaign_YYYY-MM-DD_HHMMSS.db`
