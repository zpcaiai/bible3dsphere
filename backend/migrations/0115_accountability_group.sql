-- Migration 0115: 属灵同伴 / 小组监督 Accountability Group（B7 Skill 26）
-- 同意制群组监督:目标、打卡、代祷、彼此鼓励。区别于既有个人版 accountability.py。
-- 成员自选 sharing_scope;私密认罪/危机不入群;领袖只见被允许的摘要。email 标识用户。

CREATE TABLE IF NOT EXISTS accountability_groups (
    id            VARCHAR(64)  PRIMARY KEY,
    name          VARCHAR(160) NOT NULL,
    description   TEXT         DEFAULT '',
    group_type    VARCHAR(24)  DEFAULT 'small_group',
    created_by_email VARCHAR(255) NOT NULL,
    visibility    VARCHAR(20)  DEFAULT 'private',
    status        VARCHAR(12)  DEFAULT 'active',
    group_rule    TEXT         DEFAULT '',
    confidentiality_commitment TEXT DEFAULT '彼此分享的内容在组内保密;危机与安全问题可在征得同意后升级到牧养。',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acc_groups_creator ON accountability_groups (created_by_email);

CREATE TABLE IF NOT EXISTS accountability_group_members (
    id            VARCHAR(64)  PRIMARY KEY,
    group_id      VARCHAR(64)  NOT NULL,
    email         VARCHAR(255) NOT NULL,
    role          VARCHAR(12)  DEFAULT 'member',  -- member/leader/mentor/admin
    status        VARCHAR(12)  DEFAULT 'active',  -- invited/active/paused/left/removed
    sharing_scope VARCHAR(24)  DEFAULT 'checkin_only',
    joined_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acc_members_group ON accountability_group_members (group_id, status);
CREATE INDEX IF NOT EXISTS idx_acc_members_email ON accountability_group_members (email, status);

CREATE TABLE IF NOT EXISTS accountability_group_goals (
    id          VARCHAR(64)  PRIMARY KEY,
    group_id    VARCHAR(64)  NOT NULL,
    email       VARCHAR(255) NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT         DEFAULT '',
    goal_type   VARCHAR(20)  DEFAULT 'prayer',
    status      VARCHAR(12)  DEFAULT 'active',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acc_goals_group ON accountability_group_goals (group_id, status);

CREATE TABLE IF NOT EXISTS accountability_group_checkins (
    id             VARCHAR(64)  PRIMARY KEY,
    group_id       VARCHAR(64)  NOT NULL,
    email          VARCHAR(255) NOT NULL,
    checkin_date   DATE         DEFAULT CURRENT_DATE,
    checkin_type   VARCHAR(12)  DEFAULT 'weekly',
    gratitude      TEXT         DEFAULT '',
    struggle       TEXT         DEFAULT '',
    prayer_request TEXT         DEFAULT '',
    support_needed BOOLEAN      DEFAULT FALSE,
    visibility     VARCHAR(20)  DEFAULT 'group_visible',
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acc_checkins_group ON accountability_group_checkins (group_id, checkin_date DESC);

CREATE TABLE IF NOT EXISTS group_prayer_requests (
    id              VARCHAR(64)  PRIMARY KEY,
    group_id        VARCHAR(64)  NOT NULL,
    email           VARCHAR(255) NOT NULL,
    title           VARCHAR(200) NOT NULL,
    request_text    TEXT         DEFAULT '',
    privacy_level   VARCHAR(16)  DEFAULT 'group_visible',  -- group_visible/leader_only/anonymized
    status          VARCHAR(12)  DEFAULT 'active',
    answered_summary TEXT        DEFAULT '',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_group_prayers_group ON group_prayer_requests (group_id, status);
