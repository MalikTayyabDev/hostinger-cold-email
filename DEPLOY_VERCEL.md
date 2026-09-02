# Deployment guide — GitHub → Supabase → Vercel → Hostinger SMTP

This guide follows the recommended order:

1. **Prepare locally** (already done in this repo)
2. **Push to GitHub**
3. **Create Supabase project + run schema**
4. **Deploy to Vercel + set env vars**
5. **Connect Hostinger SMTP/IMAP**
6. **Go live**

---

## Phase 1 — Push to GitHub

```powershell
cd hostinger_cold_email_system
git init
git add .
git commit -m "Cold email system — Supabase + Vercel ready"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

**Never commit:** `.env`, `*.db`, `.venv/`

---

## Phase 2 — Supabase setup

1. Go to [supabase.com](https://supabase.com) → **New project**
2. Open **SQL Editor** → paste contents of `supabase/schema.sql` → **Run**
3. Go to **Project Settings → Database**
4. Copy **Connection string (URI)** — use **Transaction pooler** (port 6543) for Vercel:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. Save for Vercel as `DATABASE_URL`

Optional (for Supabase dashboard/API later):
- `SUPABASE_URL` = Project URL
- `SUPABASE_SERVICE_KEY` = service_role key (server-side only)

---

## Phase 3 — Vercel deploy

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repo
3. **Framework:** Other
4. **Root directory:** `hostinger_cold_email_system` (if repo root is parent folder)
5. Deploy (first deploy may fail until env vars are set — that's OK)

### Environment variables (Vercel → Settings → Environment Variables)

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Supabase pooler connection string |
| `CRON_SECRET` | Random string (e.g. `openssl rand -hex 32`) |
| `SECRET_KEY` | Random string for Flask sessions |
| `PUBLIC_BASE_URL` | `https://your-app.vercel.app` (update after deploy) |
| `DRY_RUN` | `true` initially |
| `SMTP_HOST` | `smtp.hostinger.com` |
| `SMTP_PORT` | `465` |
| `SMTP_ENCRYPTION` | `ssl` |
| `SMTP_USER` | your Hostinger email |
| `SMTP_PASSWORD` | your mailbox password |
| `FROM_NAME` | Your Name |
| `FROM_EMAIL` | your Hostinger email |
| `IMAP_HOST` | `imap.hostinger.com` |
| `IMAP_PORT` | `993` |
| `IMAP_USER` | your Hostinger email |
| `IMAP_PASSWORD` | your mailbox password |
| `ADMIN_USERNAME` | dashboard login |
| `ADMIN_PASSWORD` | dashboard password |
| `DAILY_SEND_LIMIT` | `20` |
| `TEST_EMAIL` | your email for test sends |

6. **Redeploy** after adding env vars
7. Update `PUBLIC_BASE_URL` to your actual Vercel URL

---

## Phase 4 — Cron jobs (automatic sending)

`vercel.json` already configures:

| Cron | Schedule | Purpose |
|------|----------|---------|
| `/api/cron/inbox` | Every 15 min | Check IMAP for replies/unsubscribes |
| `/api/cron/send` | Every 15 min | Send **1** eligible email |

> **Note:** Vercel Cron on frequent schedules may require **Pro plan**. Each send cron sends only 1 email per run (serverless-safe).

Cron endpoints require header:
```
Authorization: Bearer YOUR_CRON_SECRET
```
Vercel Cron automatically sends this when `CRON_SECRET` is set.

---

## Phase 5 — Go live checklist

- [ ] Supabase schema applied
- [ ] Vercel deployed with all env vars
- [ ] `PUBLIC_BASE_URL` set to HTTPS Vercel URL
- [ ] Dashboard login works (`ADMIN_USERNAME` / `ADMIN_PASSWORD`)
- [ ] Import leads via dashboard
- [ ] Create/edit campaign → **Start** campaign
- [ ] Test with `DRY_RUN=true` first
- [ ] Send test email from campaign preview
- [ ] Set `DRY_RUN=false` when ready
- [ ] Verify cron runs in Vercel → Logs

---

## Local development (unchanged)

Without `DATABASE_URL`, the app uses SQLite locally:

```powershell
python app.py
python scheduler.py   # local continuous scheduler
pytest
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DB connection error on Vercel | Use Supabase **pooler** URL (port 6543), not direct 5432 |
| Cron 401 | Set `CRON_SECRET` in Vercel env |
| SMTP timeout on Vercel | Normal for batch sends — cron sends 1 email per run |
| Unsubscribe links broken | Set `PUBLIC_BASE_URL` to your Vercel HTTPS URL |

See also [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
