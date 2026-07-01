-- 0143_chinese_devotion.sql — 华人本土灵修 / Chinese Devotional Voices
CREATE TABLE IF NOT EXISTS chinese_devotion_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    need          TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chinese_devotion_email_created ON chinese_devotion_entries (email, created_at DESC);
