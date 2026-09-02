import os
import sqlite3
from datetime import datetime, timezone


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def _table_exists(con, name):
    backend = getattr(con, "backend", "sqlite")
    if backend == "postgres":
        row = con.execute(
            """SELECT 1 FROM information_schema.tables
               WHERE table_schema='public' AND table_name=%s""",
            (name,),
        ).fetchone()
        return row is not None
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _column_exists(con, table, column):
    backend = getattr(con, "backend", "sqlite")
    if backend == "postgres":
        row = con.execute(
            """SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name=%s AND column_name=%s""",
            (table, column),
        ).fetchone()
        return row is not None
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


_COLUMN_CACHE = {}


def column_exists_cached(con, table, column):
    raw = getattr(con, "_raw", con)
    cache_key = (id(raw), table, column)
    if cache_key not in _COLUMN_CACHE:
        _COLUMN_CACHE[cache_key] = _column_exists(con, table, column)
    return _COLUMN_CACHE[cache_key]


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    user_id INTEGER,
    daily_send_limit INTEGER,
    delay_min_seconds INTEGER,
    delay_max_seconds INTEGER,
    signature_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS campaign_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    UNIQUE(campaign_id, step_number)
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    full_name TEXT DEFAULT '',
    company TEXT DEFAULT '',
    email TEXT NOT NULL,
    website TEXT DEFAULT '',
    industry TEXT DEFAULT '',
    location TEXT DEFAULT '',
    custom_line TEXT DEFAULT '',
    opener_angle TEXT DEFAULT 'auto',
    tags TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    unsubscribe_token TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(email)
);

CREATE TABLE IF NOT EXISTS campaign_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    lead_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    sequence_step INTEGER NOT NULL DEFAULT 0,
    emails_sent INTEGER NOT NULL DEFAULT 0,
    replies_count INTEGER NOT NULL DEFAULT 0,
    last_contacted_at TEXT,
    next_action_at TEXT,
    replied_at TEXT,
    reply_subject TEXT,
    reply_message_id TEXT,
    bounced_at TEXT,
    bounce_reason TEXT,
    unsubscribed_at TEXT,
    send_lock_until TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    UNIQUE(campaign_id, lead_id)
);

CREATE TABLE IF NOT EXISTS email_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    lead_id INTEGER,
    campaign_lead_id INTEGER,
    event_type TEXT NOT NULL,
    details TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (campaign_lead_id) REFERENCES campaign_leads(id)
);

CREATE TABLE IF NOT EXISTS suppressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    source TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scheduler_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    job_title TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    tagline TEXT NOT NULL DEFAULT '',
    services TEXT NOT NULL DEFAULT '',
    website_url TEXT NOT NULL DEFAULT '',
    instagram_url TEXT NOT NULL DEFAULT '',
    facebook_url TEXT NOT NULL DEFAULT '',
    google_url TEXT NOT NULL DEFAULT '',
    logo_url TEXT NOT NULL DEFAULT '',
    footer_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


DEFAULT_STEPS = [
    (1, "Better web work for {{company}} — without the agency price tag", """Hi {{first_name}},

{{smart_opener}}

At LaunchNest (https://launch-nest.com) we help with full-stack development, Shopify, WordPress, UI/UX, SEO, and QA — at lean budgets vs typical agencies.

Would a quick 15-minute call make sense for {{company}}?

{{unsubscribe_footer}}""", 0),
    (2, "Re: web project for {{company}}", """Hi {{first_name}},

Following up — happy to send relevant LaunchNest examples and a rough budget range for {{company}}.

Worth a reply?

{{unsubscribe_footer}}""", 3),
    (3, "Last note — {{company}}", """Hi {{first_name}},

Last follow-up from me. If website work is not a priority, just say so and I will close the loop.

{{unsubscribe_footer}}""", 7),
    (4, "Closing the loop", """Hi {{first_name}},

All the best — reach us at launch-nest.com if {{company}} needs help later.

{{sender_name}}

{{unsubscribe_footer}}""", 14),
]


def _create_indexes(con):
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(lower(email))",
        "CREATE INDEX IF NOT EXISTS idx_cl_campaign ON campaign_leads(campaign_id)",
        "CREATE INDEX IF NOT EXISTS idx_cl_status ON campaign_leads(status)",
        "CREATE INDEX IF NOT EXISTS idx_cl_next_action ON campaign_leads(next_action_at)",
        "CREATE INDEX IF NOT EXISTS idx_events_type_date ON email_events(event_type, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_events_campaign ON email_events(campaign_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_suppressions_email ON suppressions(lower(email))",
    ]
    for sql in indexes:
        con.execute(sql)


def _migrate_legacy(con):
    """Migrate old flat leads/events tables if present."""
    if not _table_exists(con, "leads"):
        return
    if _column_exists(con, "leads", "first_name"):
        return

    legacy = con.execute("SELECT * FROM leads").fetchall()
    legacy_events = []
    if _table_exists(con, "events"):
        legacy_events = con.execute("SELECT * FROM events").fetchall()

    con.execute("ALTER TABLE leads RENAME TO leads_legacy")
    if _table_exists(con, "events"):
        con.execute("ALTER TABLE events RENAME TO events_legacy")

    con.execute("""
    CREATE TABLE leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT DEFAULT '',
        last_name TEXT DEFAULT '',
        full_name TEXT DEFAULT '',
        company TEXT DEFAULT '',
        email TEXT NOT NULL,
        website TEXT DEFAULT '',
        industry TEXT DEFAULT '',
        location TEXT DEFAULT '',
        custom_line TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        unsubscribe_token TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(email)
    )
    """)
    con.commit()

    now = utcnow_iso()
    campaign_id = con.execute(
        "INSERT INTO campaigns(name, description, status, created_at, updated_at) VALUES(?,?,?,?,?)",
        ("Migrated Campaign", "Auto-migrated from legacy schema", "active", now, now),
    ).lastrowid

    for step_num, subject, body, delay in DEFAULT_STEPS:
        con.execute(
            """INSERT INTO campaign_steps(campaign_id, step_number, subject, body, delay_days, enabled)
               VALUES(?,?,?,?,?,1)""",
            (campaign_id, step_num, subject, body, delay),
        )

    status_map = {
        "pending": "pending",
        "sent": "active",
        "followup_1_sent": "active",
        "replied": "replied",
        "unsubscribed": "unsubscribed",
        "completed": "completed",
        "bounced": "bounced",
        "paused": "paused",
    }

    for row in legacy:
        email = (row["email"] or "").strip().lower()
        name = row["name"] or ""
        parts = name.split(None, 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""

        try:
            lead_id = con.execute(
                """INSERT INTO leads(
                    first_name, last_name, full_name, company, email, website,
                    custom_line, unsubscribe_token, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    first,
                    last,
                    name,
                    row["company"] or "",
                    email,
                    row["website"] or "",
                    row["custom_line"] or "",
                    row["unsubscribe_token"] if "unsubscribe_token" in row.keys() else None,
                    row["created_at"] or now,
                ),
            ).lastrowid
        except sqlite3.IntegrityError:
            lead_id = con.execute(
                "SELECT id FROM leads WHERE lower(email)=lower(?)",
                (email,),
            ).fetchone()["id"]

        status = status_map.get(row["status"], "pending")
        con.execute(
            """INSERT OR IGNORE INTO campaign_leads(
                campaign_id, lead_id, status, sequence_step, emails_sent,
                last_contacted_at, next_action_at, replied_at, unsubscribed_at, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                campaign_id,
                lead_id,
                status,
                row["sequence_step"] or 0,
                row["sequence_step"] or 0,
                row["last_sent_at"],
                row["next_action_at"],
                row["replied_at"],
                row["unsubscribed_at"],
                row["created_at"] or now,
            ),
        )

        if status == "unsubscribed" and email:
            con.execute(
                "INSERT OR IGNORE INTO suppressions(email, reason, source, created_at) VALUES(?,?,?,?)",
                (email, "migrated unsubscribe", "migration", now),
            )

    for ev in legacy_events:
            lead_id = ev["lead_id"]
            cl = con.execute(
                "SELECT id, campaign_id FROM campaign_leads WHERE lead_id=? LIMIT 1",
                (lead_id,),
            ).fetchone()
            event_type = ev["event_type"]
            if event_type == "replied":
                event_type = "reply_detected"
            con.execute(
                """INSERT INTO email_events(campaign_id, lead_id, campaign_lead_id, event_type, details, created_at)
                   VALUES(?,?,?,?,?,?)""",
                (
                    cl["campaign_id"] if cl else None,
                    lead_id,
                    cl["id"] if cl else None,
                    event_type,
                    ev["details"] or "",
                    ev["created_at"] or now,
                ),
            )

    con.commit()


def _ensure_default_campaign(con):
    row = con.execute("SELECT COUNT(*) AS c FROM campaigns").fetchone()
    count = row["c"] if row else 0
    if count:
        return
    now = utcnow_iso()
    admin = con.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    user_id = admin["id"] if admin else None
    cid = con.execute(
        """INSERT INTO campaigns(name, description, status, user_id, daily_send_limit,
           delay_min_seconds, delay_max_seconds, created_at, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        ("Website Outreach", "Default outreach campaign", "draft", user_id, None, None, None, now, now),
    ).lastrowid
    for step_num, subject, body, delay in DEFAULT_STEPS:
        enabled = 1 if step_num <= 3 else 0
        con.execute(
            """INSERT INTO campaign_steps(campaign_id, step_number, subject, body, delay_days, enabled)
               VALUES(?,?,?,?,?,?)""",
            (cid, step_num, subject, body, delay, enabled),
        )
    con.commit()


def _migrate_multi_user(con):
    backend = getattr(con, "backend", "sqlite")
    if not _table_exists(con, "user_settings"):
        con.execute(
            """CREATE TABLE user_settings (
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (user_id, key),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )
        con.commit()

    if _table_exists(con, "campaigns") and not _column_exists(con, "campaigns", "user_id"):
        con.execute("ALTER TABLE campaigns ADD COLUMN user_id INTEGER")
        con.commit()
        admin = con.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        if admin:
            con.execute("UPDATE campaigns SET user_id=? WHERE user_id IS NULL", (admin["id"],))
            con.commit()

    if backend == "sqlite":
        con.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id)")
        con.commit()


def _migrate_signatures(con):
    backend = getattr(con, "backend", "sqlite")
    if not _table_exists(con, "email_signatures"):
        if backend == "postgres":
            con.execute(
                """CREATE TABLE email_signatures (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    job_title TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    tagline TEXT NOT NULL DEFAULT '',
                    services TEXT NOT NULL DEFAULT '',
                    website_url TEXT NOT NULL DEFAULT '',
                    instagram_url TEXT NOT NULL DEFAULT '',
                    facebook_url TEXT NOT NULL DEFAULT '',
                    google_url TEXT NOT NULL DEFAULT '',
                    logo_url TEXT NOT NULL DEFAULT '',
                    footer_text TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )"""
            )
        else:
            con.execute(
                """CREATE TABLE email_signatures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    job_title TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    tagline TEXT NOT NULL DEFAULT '',
                    services TEXT NOT NULL DEFAULT '',
                    website_url TEXT NOT NULL DEFAULT '',
                    instagram_url TEXT NOT NULL DEFAULT '',
                    facebook_url TEXT NOT NULL DEFAULT '',
                    google_url TEXT NOT NULL DEFAULT '',
                    logo_url TEXT NOT NULL DEFAULT '',
                    footer_text TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )"""
            )
        con.commit()

    if _table_exists(con, "campaigns") and not _column_exists(con, "campaigns", "signature_id"):
        con.execute("ALTER TABLE campaigns ADD COLUMN signature_id INTEGER")
        con.commit()

    if backend == "sqlite" and _table_exists(con, "email_signatures"):
        con.execute("CREATE INDEX IF NOT EXISTS idx_email_signatures_user ON email_signatures(user_id)")
        con.commit()


def _migrate_opener_angle(con):
    if _table_exists(con, "leads") and not _column_exists(con, "leads", "opener_angle"):
        con.execute("ALTER TABLE leads ADD COLUMN opener_angle TEXT DEFAULT 'auto'")
        con.commit()


def connect(path="campaign.db"):
    # Explicit sqlite path (e.g. tests) must not be overridden by DATABASE_URL.
    if os.getenv("DATABASE_URL") and path == "campaign.db":
        from database.adapter import connect_postgres
        con = connect_postgres(os.getenv("DATABASE_URL"))
        # Migrations are slow on Supabase pooler — run migration_multi_user.sql manually.
        if not os.getenv("VERCEL"):
            _migrate_multi_user(con)
            _migrate_signatures(con)
            _migrate_opener_angle(con)
            _ensure_default_campaign(con)
        return con

    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    con.commit()
    _migrate_legacy(con)
    _migrate_multi_user(con)
    _migrate_signatures(con)
    _migrate_opener_angle(con)
    _ensure_default_campaign(con)
    _create_indexes(con)
    con.commit()
    return con


def add_event(con, campaign_id, lead_id, campaign_lead_id, event_type, details=""):
    con.execute(
        """INSERT INTO email_events(campaign_id, lead_id, campaign_lead_id, event_type, details, created_at)
           VALUES(?,?,?,?,?,?)""",
        (campaign_id, lead_id, campaign_lead_id, event_type, details, utcnow_iso()),
    )
    con.commit()


def daily_sent_count(con, campaign_id=None):
    today = datetime.now(timezone.utc).date().isoformat()
    backend = getattr(con, "backend", "sqlite")

    if backend == "postgres":
        if campaign_id:
            row = con.execute(
                """SELECT COUNT(*) AS c FROM email_events
                   WHERE event_type='sent'
                     AND created_at::date = CURRENT_DATE
                     AND campaign_id=%s""",
                (campaign_id,),
            ).fetchone()
        else:
            row = con.execute(
                """SELECT COUNT(*) AS c FROM email_events
                   WHERE event_type='sent'
                     AND created_at::date = CURRENT_DATE""",
            ).fetchone()
    else:
        if campaign_id:
            row = con.execute(
                """SELECT COUNT(*) c FROM email_events
                   WHERE event_type='sent' AND created_at LIKE ? AND campaign_id=?""",
                (today + "%", campaign_id),
            ).fetchone()
        else:
            row = con.execute(
                """SELECT COUNT(*) c FROM email_events
                   WHERE event_type='sent' AND created_at LIKE ?""",
                (today + "%",),
            ).fetchone()
    return row["c"]
