-- 0138_emotionally_healthy.sql — 情商与灵命 / Emotionally Healthy Spirituality (Scazzero)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS eh_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    text          TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_eh_email_created ON eh_entries (email, created_at DESC);
