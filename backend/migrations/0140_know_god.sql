-- 0140_know_god.sql — 认识神 / Knowing God (Packer《认识神》/ Tozer / Reeves)，按神的属性默想。
-- content-theology-expansion 批次；email-keyed；幂等。
CREATE TABLE IF NOT EXISTS know_god_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    need_text     TEXT NOT NULL DEFAULT '',
    attribute     VARCHAR(64) NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_know_god_email_created ON know_god_entries (email, created_at DESC);
