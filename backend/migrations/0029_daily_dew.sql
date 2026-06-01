-- Migration 0029: 清晨甘露每日缓存（全站共享，避免重复调用 AI）
CREATE TABLE IF NOT EXISTS daily_dew (
    dew_date     DATE         NOT NULL,
    tier         INTEGER      NOT NULL,
    content_json JSONB        NOT NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dew_date, tier)
);
