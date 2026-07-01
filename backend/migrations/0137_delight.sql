-- 0137_delight.sql — 喜乐重构 / Christian Hedonism (Piper《Desiring God》)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS delight_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    duty          TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_delight_email_created ON delight_entries (email, created_at DESC);
