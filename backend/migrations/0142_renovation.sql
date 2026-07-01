-- 0142_renovation.sql — 心意更新 / Renovation of the Heart (Willard VIM×五维)
CREATE TABLE IF NOT EXISTS renovation_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    scores        JSONB NOT NULL DEFAULT '{}'::jsonb,
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_renovation_email_created ON renovation_entries (email, created_at DESC);
