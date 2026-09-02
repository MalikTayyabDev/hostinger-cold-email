-- Run in Supabase SQL Editor (optional — smart openers work without this, but opener_angle per lead needs it)

ALTER TABLE leads ADD COLUMN IF NOT EXISTS opener_angle TEXT DEFAULT 'auto';
