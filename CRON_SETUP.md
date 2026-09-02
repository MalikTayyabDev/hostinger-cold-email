# Cron setup on Vercel Hobby (free plan)

Vercel **Hobby** only allows **once-per-day** cron jobs.  
Our app needs checks every **15 minutes** for sending and inbox.

**Solution:** Use a free external cron service to call your API endpoints.

---

## Your cron endpoints

Replace `YOUR-APP.vercel.app` with your Vercel URL.

| Endpoint | Purpose |
|----------|---------|
| `https://YOUR-APP.vercel.app/api/cron/inbox` | Check IMAP for replies/unsubscribes |
| `https://YOUR-APP.vercel.app/api/cron/send` | Send 1 eligible email |

Both require this header:

```text
Authorization: Bearer YOUR_CRON_SECRET
```

(`YOUR_CRON_SECRET` = the value you set in Vercel env vars)

---

## Option A — cron-job.org (recommended, free)

1. Go to [cron-job.org](https://cron-job.org) → create free account
2. **Create cronjob** → **Title:** `Cold Email - Inbox`
   - **URL:** `https://YOUR-APP.vercel.app/api/cron/inbox`
   - **Schedule:** every 15 minutes
   - **Request method:** GET or POST
   - **Headers:** add header:
     - Name: `Authorization`
     - Value: `Bearer YOUR_CRON_SECRET`
3. Create second job **Cold Email - Send**
   - **URL:** `https://YOUR-APP.vercel.app/api/cron/send`
   - Same schedule and header

---

## Option B — Manual sending (no cron)

Use the dashboard:

- **Send one** or **Send eligible batch**

Good for testing; not automatic.

---

## Option C — Local scheduler (your PC)

```powershell
cd hostinger_cold_email_system
.\.venv\Scripts\activate
# Set DATABASE_URL in .env to Supabase pooler URL
python scheduler.py
```

Keeps running while your PC is on.

---

## Option D — Vercel Pro ($20/mo)

Pro unlocks frequent Vercel Cron. You can add this back to `vercel.json`:

```json
"crons": [
  { "path": "/api/cron/inbox", "schedule": "*/15 * * * *" },
  { "path": "/api/cron/send", "schedule": "*/15 * * * *" }
]
```

---

## Test cron manually

In PowerShell (replace URL and secret):

```powershell
Invoke-WebRequest -Uri "https://YOUR-APP.vercel.app/api/cron/send" -Headers @{ Authorization = "Bearer YOUR_CRON_SECRET" }
```

Success response example:

```json
{"ok": true, "sent": 0, "failed": 0}
```

---

## Summary

| Plan | Automatic sending |
|------|-------------------|
| Vercel Hobby + cron-job.org | Yes (free) |
| Vercel Hobby only | Manual or once/day |
| Vercel Pro | Built-in every 15 min |
| Local `scheduler.py` | Yes while PC runs |
