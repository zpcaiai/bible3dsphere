-- Migration 0032: 决策辨识（司布真版）
CREATE TABLE IF NOT EXISTS decision_discernments (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    situation     TEXT         DEFAULT '',
    options_json  JSONB        DEFAULT '[]'::jsonb,
    recommended   INTEGER      DEFAULT 0,
    analysis_json JSONB        DEFAULT '{}'::jsonb,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_discern_email_created ON decision_discernments (email, created_at DESC);
