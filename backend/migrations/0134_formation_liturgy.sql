-- 0134_formation_liturgy.sql — 塑造礼仪 / You Are What You Love (James K.A. Smith)
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS formation_liturgy_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    liturgy       TEXT NOT NULL DEFAULT '',
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_liturgy_email_created ON formation_liturgy_entries (email, created_at DESC);
