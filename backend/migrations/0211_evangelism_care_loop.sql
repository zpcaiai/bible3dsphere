-- 0211: 传FY 闭环 — 挂念名单、每日代祷打卡、见证审核
-- Design: docs/传FY与宣教重设计方案.md (Phase 1)

CREATE TABLE IF NOT EXISTS evangelism_contacts (
    id           SERIAL PRIMARY KEY,
    owner_email  VARCHAR(255) NOT NULL,
    display_name VARCHAR(60)  NOT NULL,          -- 仅称呼/昵称，隐私最小化
    stage        VARCHAR(20)  NOT NULL DEFAULT 'not_yet'
                 CHECK (stage IN ('not_yet','curious','seeking','decided','baptized','walking')),
    notes        VARCHAR(500) NOT NULL DEFAULT '',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at   TIMESTAMP DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_evangelism_contacts_owner
    ON evangelism_contacts(owner_email) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS evangelism_prayer_logs (
    id          SERIAL PRIMARY KEY,
    contact_id  INTEGER NOT NULL REFERENCES evangelism_contacts(id) ON DELETE CASCADE,
    owner_email VARCHAR(255) NOT NULL,
    prayed_on   DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (contact_id, prayed_on)
);
CREATE INDEX IF NOT EXISTS idx_evangelism_prayer_logs_owner
    ON evangelism_prayer_logs(owner_email, prayed_on DESC);

-- 祷告墙帖子类型与见证审核状态
ALTER TABLE evangelism_prayers ADD COLUMN IF NOT EXISTS kind VARCHAR(16) NOT NULL DEFAULT 'prayer';
ALTER TABLE evangelism_prayers ADD COLUMN IF NOT EXISTS review_status VARCHAR(16) NOT NULL DEFAULT 'approved';
-- kind: 'prayer' | 'testimony'; review_status: 'approved' | 'pending' | 'rejected'
CREATE INDEX IF NOT EXISTS idx_evangelism_prayers_review
    ON evangelism_prayers(review_status) WHERE review_status <> 'approved';
