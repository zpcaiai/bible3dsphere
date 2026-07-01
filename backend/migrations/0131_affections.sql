-- 0131_affections.sql — 宗教情感真伪辨 / Religious Affections (Edwards 可靠记号)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS affections_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_affections_email_created ON affections_entries (email, created_at DESC);
