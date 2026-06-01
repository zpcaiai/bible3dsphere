-- Migration 0030: 属灵低潮体检（钟马田）
CREATE TABLE IF NOT EXISTS spiritual_checkups (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    ratings       JSONB        DEFAULT '{}'::jsonb,
    index_score   REAL         DEFAULT 0,
    level         VARCHAR(16)  DEFAULT '',
    summary       TEXT         DEFAULT '',
    analysis_json JSONB        DEFAULT '{}'::jsonb,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_checkup_email_created ON spiritual_checkups (email, created_at DESC);
