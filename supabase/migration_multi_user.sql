-- Multi-user migration — run once in Supabase SQL Editor after schema.sql

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);

-- Assign existing campaigns to the first user (usually admin)
UPDATE campaigns
SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1)
WHERE user_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns (user_id);
