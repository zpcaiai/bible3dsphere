-- 0136_union.sql — 与基督联合·身份 / Union with Christ（在基督里我是谁）
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS union_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    identity_key  TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_union_email_created ON union_entries (email, created_at DESC);
