-- Migration 0027: 感恩日记 + 灵修问责（属灵目标 + 周/日问责）
-- 用户以 email 标识，日期 Asia/Shanghai。认罪与赦免不落库（隐私），故无表。

-- 感恩日记（数算恩典）：一天可多条
CREATE TABLE IF NOT EXISTS gratitude_entries (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    content     TEXT         NOT NULL,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_grat_email ON gratitude_entries (email, created_at DESC);

-- 灵修问责：属灵目标
CREATE TABLE IF NOT EXISTS accountability_goals (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    title       VARCHAR(200) NOT NULL,
    detail      TEXT         DEFAULT '',
    cadence     VARCHAR(20)  DEFAULT 'daily',   -- daily | weekly
    active      BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acc_goals_email ON accountability_goals (email, active);

-- 灵修问责：打卡记录
CREATE TABLE IF NOT EXISTS accountability_checkins (
    id          VARCHAR(64)  PRIMARY KEY,
    goal_id     VARCHAR(64)  NOT NULL REFERENCES accountability_goals(id) ON DELETE CASCADE,
    email       VARCHAR(255) NOT NULL,
    status      VARCHAR(20)  DEFAULT 'done',    -- done | partial | missed
    note        TEXT         DEFAULT '',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acc_checkins_goal ON accountability_checkins (goal_id, created_at DESC);
