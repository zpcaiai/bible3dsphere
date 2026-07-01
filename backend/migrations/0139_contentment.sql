-- 0139_contentment.sql — 知足 / Christian Contentment (Jeremiah Burroughs《基督徒知足的秘诀》)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS contentment_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    lack_text     TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    prayer        TEXT NOT NULL DEFAULT '',
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_contentment_email_created ON contentment_entries (email, created_at DESC);
