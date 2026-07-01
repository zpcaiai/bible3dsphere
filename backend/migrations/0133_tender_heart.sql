-- 0133_tender_heart.sql — 温柔谦卑 / Gentle and Lowly (Dane Ortlund)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS tender_heart_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    lie           TEXT NOT NULL DEFAULT '',
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tender_heart_email_created ON tender_heart_entries (email, created_at DESC);
