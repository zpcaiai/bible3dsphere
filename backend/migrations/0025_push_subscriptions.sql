-- Migration 0025: Web Push 订阅 + 晨更/晚祷提醒偏好
-- 每个浏览器端点一条订阅。提醒时间以 Asia/Shanghai 本地时间 HH:MM 表示。

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id                 VARCHAR(64)  PRIMARY KEY,
    email              VARCHAR(255) NOT NULL,
    endpoint           TEXT         NOT NULL,
    p256dh             TEXT         NOT NULL,
    auth               TEXT         NOT NULL,

    enabled            BOOLEAN      DEFAULT TRUE,
    morning_on         BOOLEAN      DEFAULT TRUE,
    evening_on         BOOLEAN      DEFAULT TRUE,
    morning_time       VARCHAR(5)   DEFAULT '07:00',
    evening_time       VARCHAR(5)   DEFAULT '21:30',

    last_morning_sent  DATE,
    last_evening_sent  DATE,

    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (email, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_push_email   ON push_subscriptions (email);
CREATE INDEX IF NOT EXISTS idx_push_enabled ON push_subscriptions (enabled) WHERE enabled = TRUE;
