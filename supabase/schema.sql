-- Supabase / PostgreSQL schema for Cold Email System
-- Run this in Supabase SQL Editor after creating your project.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    daily_send_limit INTEGER,
    delay_min_seconds INTEGER,
    delay_max_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_steps (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    UNIQUE(campaign_id, step_number)
);

CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    full_name TEXT DEFAULT '',
    company TEXT DEFAULT '',
    email TEXT NOT NULL UNIQUE,
    website TEXT DEFAULT '',
    industry TEXT DEFAULT '',
    location TEXT DEFAULT '',
    custom_line TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    unsubscribe_token TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_leads (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    sequence_step INTEGER NOT NULL DEFAULT 0,
    emails_sent INTEGER NOT NULL DEFAULT 0,
    replies_count INTEGER NOT NULL DEFAULT 0,
    last_contacted_at TIMESTAMPTZ,
    next_action_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    reply_subject TEXT,
    reply_message_id TEXT,
    bounced_at TIMESTAMPTZ,
    bounce_reason TEXT,
    unsubscribed_at TIMESTAMPTZ,
    send_lock_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_id, lead_id)
);

CREATE TABLE IF NOT EXISTS email_events (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    lead_id INTEGER REFERENCES leads(id),
    campaign_lead_id INTEGER REFERENCES campaign_leads(id),
    event_type TEXT NOT NULL,
    details TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS suppressions (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    source TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads (lower(email));
CREATE INDEX IF NOT EXISTS idx_cl_campaign ON campaign_leads (campaign_id);
CREATE INDEX IF NOT EXISTS idx_cl_status ON campaign_leads (status);
CREATE INDEX IF NOT EXISTS idx_cl_next_action ON campaign_leads (next_action_at);
CREATE INDEX IF NOT EXISTS idx_events_type_date ON email_events (event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_events_campaign ON email_events (campaign_id, created_at);
CREATE INDEX IF NOT EXISTS idx_suppressions_email ON suppressions (lower(email));

-- Default campaign + sequence (safe to re-run: skips if campaign exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM campaigns LIMIT 1) THEN
        INSERT INTO campaigns (name, description, status, created_at, updated_at)
        VALUES ('Website Outreach', 'Default outreach campaign', 'draft', NOW(), NOW());

        INSERT INTO campaign_steps (campaign_id, step_number, subject, body, delay_days, enabled) VALUES
        (1, 1, 'Quick idea for {{company}}', 'Hi {{first_name}},

{{custom_line}}

I work with businesses on website improvements, performance and conversion-focused fixes. I had a couple of specific ideas for {{company}}.

Would you be open to me sending them over?

Best,
{{sender_name}}

{{email_footer}}
{{unsubscribe_footer}}', 0, 1),
        (1, 2, 'Re: Quick idea for {{company}}', 'Hi {{first_name}},

Just following up on my note below.

If improving the website isn''t a priority right now, no worries — just let me know and I won''t follow up again.

Best,
{{sender_name}}

{{unsubscribe_footer}}', 3, 1),
        (1, 3, 'Last follow-up — {{company}}', 'Hi {{first_name}},

I''ll make this my last follow-up.

If you''d like the website ideas I mentioned, I''m happy to send them over. Otherwise, no problem.

Best,
{{sender_name}}

{{unsubscribe_footer}}', 7, 1),
        (1, 4, 'Checking in — {{company}}', 'Hi {{first_name}},

Wanted to check in one last time in case timing is better now.

Best,
{{sender_name}}

{{unsubscribe_footer}}', 14, 0);
    END IF;
END $$;
