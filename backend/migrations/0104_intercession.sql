-- Migration 0104: 代祷 Intercession（B2 Skill 06）
-- 为人、家庭、教会、事工、城市、国家、个人负担维护代祷名单：添加 → 规律代祷 →
-- 追踪更新 → 标记蒙应允。隐私优先：默认 private；提醒避免属灵八卦与不安全披露。
-- email 标识用户。

CREATE TABLE IF NOT EXISTS intercession_targets (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    target_type   VARCHAR(24)  DEFAULT 'person',  -- person/family/church/ministry/city/nation/workplace/school/mission/personal/custom
    display_name  VARCHAR(160) NOT NULL,
    relationship  VARCHAR(120) DEFAULT '',
    privacy_level VARCHAR(24)  DEFAULT 'private',  -- private/mentor_visible/group_visible/public_anonymized
    notes         TEXT         DEFAULT '',
    active        BOOLEAN      DEFAULT TRUE,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_intercession_targets_email ON intercession_targets (email, active);

CREATE TABLE IF NOT EXISTS intercession_requests (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    target_id       VARCHAR(64)  DEFAULT '',
    title           VARCHAR(200) NOT NULL,
    description     TEXT         DEFAULT '',
    category        VARCHAR(24)  DEFAULT 'other',   -- salvation/healing/wisdom/protection/repentance/provision/calling/relationship/suffering/ministry/justice/thanksgiving/other
    urgency         VARCHAR(12)  DEFAULT 'normal',  -- low/normal/high/urgent
    privacy_level   VARCHAR(24)  DEFAULT 'private',
    status          VARCHAR(12)  DEFAULT 'active',  -- active/paused/answered/closed
    answered_summary TEXT        DEFAULT '',
    answered_at     TIMESTAMP,
    next_pray_at    TIMESTAMP,
    last_prayed_at  TIMESTAMP,
    pray_count      INT          DEFAULT 0,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_intercession_requests_email ON intercession_requests (email, status);
CREATE INDEX IF NOT EXISTS idx_intercession_requests_due ON intercession_requests (email, next_pray_at);

CREATE TABLE IF NOT EXISTS intercession_request_updates (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    request_id  VARCHAR(64)  NOT NULL,
    update_type VARCHAR(20)  DEFAULT 'status_update', -- status_update/answered/partial_answer/burden_changed/follow_up/closed
    update_text TEXT         DEFAULT '',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_intercession_updates_req ON intercession_request_updates (request_id, created_at DESC);

CREATE TABLE IF NOT EXISTS intercession_prayer_logs (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    request_id    VARCHAR(64)  NOT NULL,
    prayer_text   TEXT         DEFAULT '',
    burden_before INT,
    burden_after  INT,
    prayed_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_intercession_logs_req ON intercession_prayer_logs (request_id, prayed_at DESC);
