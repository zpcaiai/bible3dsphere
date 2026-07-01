-- 0135_spirits.sql — 依纳爵·诸灵分辨 / Ignatian Discernment of Spirits（安慰/枯竭）
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS spirits_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    state         TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_spirits_email_created ON spirits_entries (email, created_at DESC);
