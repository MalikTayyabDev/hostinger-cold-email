-- Run in Supabase SQL Editor after schema.sql and migration_multi_user.sql

CREATE TABLE IF NOT EXISTS email_signatures (
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
);

CREATE INDEX IF NOT EXISTS idx_email_signatures_user ON email_signatures(user_id);

ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS signature_id INTEGER REFERENCES email_signatures(id) ON DELETE SET NULL;
