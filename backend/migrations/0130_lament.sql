-- 0130_lament.sql — 哀歌 / Biblical Lament (Vroegop 四步)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS lament_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    situation     TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    prayer        TEXT NOT NULL DEFAULT '',
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lament_email_created ON lament_entries (email, created_at DESC);
