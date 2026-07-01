-- 0132_ordo_amoris.sql — 失序之爱→重排 / ordo amoris (Augustine 服务端引擎版)
-- content-theology-expansion 批次；email-keyed；幂等。
-- 注意：本表 ordo_amoris_entries 属「奥古斯丁·爱的次序」引擎版，与既有
-- ordo_amoris_records（爱之秩序星图/客户端引擎）为两个不同功能，互不冲突。
CREATE TABLE IF NOT EXISTS ordo_amoris_entries (
    id            VARCHAR(64) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    input_text    TEXT NOT NULL DEFAULT '',
    crisis        BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ordo_amoris_entries_email_created ON ordo_amoris_entries (email, created_at DESC);
