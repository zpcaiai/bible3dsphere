-- Migration 0026: 读经计划进度 + 背经（SM-2 间隔重复）
-- 计划内容（经文清单）放前端静态定义；后端只存「报名 + 进度 + 背经卡片」。
-- 用户以 email 标识；日期按 Asia/Shanghai。

-- 读经计划报名（选了哪个计划 + 起始日）
CREATE TABLE IF NOT EXISTS reading_plan_enrollment (
    email       VARCHAR(255) NOT NULL,
    plan_id     VARCHAR(40)  NOT NULL,
    start_date  DATE         DEFAULT (NOW() AT TIME ZONE 'Asia/Shanghai')::date,
    active      BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (email, plan_id)
);

-- 读经计划进度（完成了哪些「天」）
CREATE TABLE IF NOT EXISTS reading_plan_progress (
    id           VARCHAR(64)  PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    plan_id      VARCHAR(40)  NOT NULL,
    day_key      VARCHAR(20)  NOT NULL,   -- 'MM-DD'(date型) 或 'd001'(顺序型)
    completed_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email, plan_id, day_key)
);
CREATE INDEX IF NOT EXISTS idx_rpp_email_plan ON reading_plan_progress (email, plan_id);

-- 背经卡片（SM-2）
CREATE TABLE IF NOT EXISTS memory_verses (
    id             VARCHAR(64)  PRIMARY KEY,
    email          VARCHAR(255) NOT NULL,
    reference      VARCHAR(120) NOT NULL,
    verse_text     TEXT         NOT NULL,
    ease           REAL         DEFAULT 2.5,
    interval_days  INTEGER      DEFAULT 0,
    repetitions    INTEGER      DEFAULT 0,
    due_date       DATE         DEFAULT (NOW() AT TIME ZONE 'Asia/Shanghai')::date,
    last_reviewed  TIMESTAMP,
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mv_email_due ON memory_verses (email, due_date);
