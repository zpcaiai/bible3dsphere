-- Migration 0031: 天路客旅程日志（记录所到之地的变化，构成「你的天路历程」时间线）
CREATE TABLE IF NOT EXISTS pilgrim_visits (
    id         VARCHAR(64)  PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    place_key  VARCHAR(40)  NOT NULL,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pilgrim_email_created ON pilgrim_visits (email, created_at DESC);
