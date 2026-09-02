# Project Audit — Hostinger Cold Email Automation

**Audit date:** 2026-09-02  
**Scope:** Full inspection of existing codebase before phased improvements.

---

## Current Architecture

### Structure

Flat, single-package layout (10 source files):

```
hostinger_cold_email_system/
├── app.py              # Flask app, routes, sending logic, templates
├── db.py               # SQLite connection + schema bootstrap
├── mailer.py           # SMTP send + IMAP reply scan
├── scheduler.py        # 15-minute loop (imports app)
├── templates/index.html
├── leads.csv
├── requirements.txt    # Flask, python-dotenv only
├── .env.example
├── .gitignore
└── README.md
```

No `tests/`, `logs/`, `services/`, `routes/`, or `models/` packages yet.

### Data Flow

```
CSV import → leads table (SQLite)
                    ↓
Dashboard / scheduler → eligible_leads() → render_message() → smtp_send()
                    ↓
              events table (sent, replied, unsubscribed)
                    ↓
IMAP find_replies() → mark_replies() → lead status = replied
```

### Flask Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dashboard (stats, leads table, import/send forms) |
| POST | `/import` | CSV upload |
| POST | `/send` | Send one eligible email |
| POST | `/send-batch` | Send N eligible emails |
| POST | `/suppress/<lead_id>` | Manual unsubscribe |
| GET/POST | `/unsubscribe/<lead_id>` | Public unsubscribe page |

### SQLite Schema

**`leads`**

| Column | Notes |
|--------|-------|
| id | PK |
| name, company, email, website, custom_line | Basic lead fields |
| status | pending, sent, followup_1_sent, replied, unsubscribed, completed |
| sequence_step | 0–3 |
| last_sent_at, next_action_at | Scheduling |
| replied_at, unsubscribed_at | Stop conditions |
| created_at | Import time |

- `email` has a global UNIQUE constraint (no campaign scoping).
- No foreign keys, indexes, or migrations framework.

**`events`**

| Column | Notes |
|--------|-------|
| id | PK |
| lead_id | Optional FK (not enforced) |
| event_type | sent, replied, unsubscribed |
| details | Free text |
| created_at | ISO timestamp |

### Email Sequence

Hard-coded 3-step sequence in `app.py`:

1. Initial (step 0) — immediate when `status=pending`
2. Follow-up 1 (step 1) — after `FOLLOWUP_1_DAYS` (default 3)
3. Follow-up 2 (step 2) — after `FOLLOWUP_2_DAYS` (default 7)

Templates use Python `{name}` formatting, not `{{variable}}` placeholders.

### Configuration (`.env`)

SMTP, IMAP, sending limits, delays, follow-up days, `DRY_RUN`, `PUBLIC_BASE_URL`, `CAMPAIGN_NAME`.

Loaded once at startup into a global `CFG` dict in `app.py`.

### Scheduler

`scheduler.py` runs an infinite loop every 15 minutes:

1. `mark_replies()` — IMAP scan
2. `send_batch()` — up to daily limit
3. Sleep 900s

Imports all logic from `app.py` (shared global DB connection).

---

## Problems Found

### Critical

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | **No per-lead error isolation** | `send_batch()` / `send_one()` | One SMTP failure aborts the entire batch |
| 2 | **Send-before-record ordering** | `send_one()` | Crash after SMTP but before DB commit → duplicate on restart |
| 3 | **No send idempotency / lock** | Scheduler + manual send | Concurrent runs can double-send |
| 4 | **Predictable unsubscribe URLs** | `/unsubscribe/<int:lead_id>` | Enumeratable; `secrets` imported but unused |
| 5 | **IMAP marks any inbox sender as replied** | `find_replies()` | Includes user's own address, newsletters, unrelated mail |
| 6 | **No CSRF protection** | All POST forms | Cross-site actions possible if dashboard exposed |
| 7 | **No authentication** | All routes | Anyone on localhost/LAN can send/suppress/import |

### High

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 8 | **README claims reply-keyword unsubscribe** | README §7 | Not implemented; only full reply = replied |
| 9 | **SMTP only supports SSL (465)** | `mailer.smtp_send()` | Port 587 STARTTLS not supported |
| 10 | **No bounce detection** | — | Bounced addresses keep receiving follow-ups |
| 11 | **No suppression table** | — | Unsubscribe tied to lead row only |
| 12 | **CSV import swallows all errors** | `import_csv()` bare `except` | Duplicates/invalid rows silently dropped |
| 13 | **No import preview or validation** | `import_csv()` | User cannot see valid/invalid/duplicate counts |
| 14 | **List-Unsubscribe-Post always set** | `mailer.smtp_send()` | Advertises one-click without verifying POST handler |
| 15 | **Failed sends not recorded** | `send_one()` | No `send_failed` events; daily count logic OK but no audit trail |

### Medium

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 16 | **No campaign system** | — | Single implicit campaign via env var |
| 17 | **Limited lead fields** | Schema | Missing first/last name, tags, industry, location, notes, bounce fields |
| 18 | **No email preview / test send** | — | Cannot preview before live send |
| 19 | **No CSV export** | — | |
| 20 | **No settings UI** | — | All config via `.env` only |
| 21 | **No structured logging** | — | Only `print()` in mailer/scheduler |
| 22 | **No tests** | — | Zero pytest coverage |
| 23 | **No backup script** | — | |
| 24 | **No pause/resume** | — | |
| 25 | **Daily count uses `LIKE 'YYYY-MM-DD%'`** | `daily_count()` | Works for ISO dates but fragile |
| 26 | **Scheduler circular import** | `scheduler.py` → `app` | Loads full Flask app at import time |
| 27 | **SQLite `check_same_thread=False`** | `db.connect()` | Required for Flask but needs careful use |
| 28 | **No file upload size limit** | `/import` | Large CSV could exhaust memory |
| 29 | **No Flask `SECRET_KEY`** | `app.py` | Blocks session/CSRF patterns |

### Low / Documentation

| # | Issue | Impact |
|---|-------|--------|
| 30 | Missing `ARCHITECTURE.md`, `SETUP_WINDOWS.md`, `TROUBLESHOOTING.md` | |
| 31 | `.gitignore` missing `logs/`, `backups/` | |
| 32 | `CAMPAIGN_NAME` env var unused in code | |
| 33 | Dashboard shows only 200 leads, no pagination/search | |
| 34 | No progress bar for daily sends | Shows count only |

---

## What Works Today

- Flask dashboard loads and renders (verified: HTTP 200).
- SQLite bootstrap creates tables on first run.
- CSV import inserts leads (basic columns).
- DRY_RUN mode prints email content without sending.
- 3-step follow-up sequence with configurable day delays.
- Template fallbacks for missing name/company/custom_line.
- Daily send cap enforced via event count.
- Randomized delay between sends in a batch.
- Manual suppression via dashboard.
- Public unsubscribe link (when `PUBLIC_BASE_URL` set).
- List-Unsubscribe header when URL configured.
- IMAP reply detection (basic, when not in DRY_RUN).
- Scheduler loop with error recovery sleep.

---

## Recommended Improvements

### Phase 1 — Audit + Obvious Bug Fixes *(current)*

- Add `PROJECT_AUDIT.md` (this document).
- Per-lead try/except in sending; record `send_failed` events.
- SMTP error handling without exposing credentials.
- Exclude own email from IMAP reply matching.
- Secure unsubscribe tokens (replace integer IDs in URLs).
- Basic structured logging to `logs/`.
- STARTTLS support for port 587.
- Only emit `List-Unsubscribe-Post` when one-click endpoint exists.
- Improve CSV import feedback (counts, don't silently swallow).
- Enable SQLite foreign keys pragma.

### Phase 2 — Database + Services Refactor

- Normalize schema: `campaigns`, `campaign_steps`, `campaign_leads`, `suppressions`, `settings`.
- Add indexes on `email`, `status`, `campaign_id`, `next_action_at`.
- Extract services: `email_service`, `imap_service`, `lead_service`, `scheduler_service`.
- Migration framework for schema changes.
- Idempotent send flow: lock → record attempt → send → finalize.

### Phase 3 — Campaign + Sequence System

- CRUD for campaigns (draft/active/paused/completed).
- Configurable sequence steps (subject, body, delay, enabled).
- Campaign selector on dashboard.
- Pause/resume campaign.

### Phase 4 — Lead Management

- Full lead fields, lead detail page, timeline.
- Search, filter, pagination, sort.
- Duplicate handling per campaign (normalized email).
- CSV import preview + export (all/filtered/campaign/suppressed).

### Phase 5 — SMTP/IMAP/Bounce/Reply

- `{{variable}}` personalization engine with safe fallbacks.
- Email preview + test send.
- Reply stores date/subject/message-id; stops follow-ups.
- Reply-keyword unsubscribe detection (careful false-positive handling).
- Bounce detection from SMTP responses.
- Suppression table enforced globally.

### Phase 6 — Dashboard/UI

- Modern SaaS-style responsive UI.
- Campaign page, leads page, settings page.
- Daily send progress bar.
- Confirmation dialogs, notifications, empty states.

### Phase 7 — Security

- Optional admin auth (hashed password).
- CSRF on all POST actions.
- Input validation, HTML escaping, upload limits.
- Bind to `127.0.0.1` by default (already done).

### Phase 8 — Testing

- pytest suite: DB, templates, mocked SMTP/IMAP, scheduler rules.
- CI-friendly; never send real email in tests.

### Phase 9 — Documentation + Ops

- Rewrite README; add `ARCHITECTURE.md`, `SETUP_WINDOWS.md`, `TROUBLESHOOTING.md`.
- `backup.py` command.
- `manage.py` CLI helpers.

---

## Implementation Order Summary

```
Phase 1  Audit + critical bug fixes          ← NOW
Phase 2  DB refactor + service layer
Phase 3  Campaigns + sequences
Phase 4  Lead management + CSV improvements
Phase 5  Email/IMAP/bounce/reply hardening
Phase 6  UI overhaul
Phase 7  Security (auth, CSRF)
Phase 8  Tests
Phase 9  Docs + backup + CLI
```

Each phase should end with: run tests, verify app still starts, document changes.

---

## Phase 1 Fixes Applied (2026-09-02)

- Per-lead SMTP error isolation; `send_failed` events recorded
- Safe SMTP error messages (no credential leakage)
- STARTTLS support via `SMTP_ENCRYPTION=starttls` or port 587
- IMAP reply detection excludes sender's own addresses
- Secure unsubscribe tokens (legacy integer URLs still work)
- `List-Unsubscribe-Post` only when `PUBLIC_BASE_URL` is configured
- CSV import: validation, 5 MB limit, import result flash message
- Structured logging to `logs/app.log`
- SQLite indexes + foreign keys pragma
- Dashboard: flash messages + daily send progress bar
- Smoke test script: `test_smoke.py`


## Target Database Design (Future)

```
users              — optional admin auth
campaigns          — name, status, limits, dates
campaign_steps     — step, subject, body, delay_days, enabled
leads              — contact fields, notes, tags
campaign_leads     — lead ↔ campaign, status, sequence position, next_action_at
email_events       — imported, queued, sent, send_failed, reply_detected, etc.
suppressions       — email, reason, created_at
settings           — non-secret app settings (secrets stay in .env)
```

---

## Security Notes

- `.env` and `*.db` are gitignored — good.
- Passwords never appear in source — good.
- Passwords could appear in SMTP exception strings or dry-run logs — needs care.
- Unsubscribe by sequential ID is weak — fix in Phase 1.
- No rate limiting on web routes — acceptable for localhost-only use.
