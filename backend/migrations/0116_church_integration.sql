-- Migration 0116: 教会生活整合 Church Integration（B7 Skill 28）
-- 连接状态、教会生活节奏、服事、教会创伤安全重返。不强迫不安全的教会/权柄;
-- 教会创伤 → 先医治 + 界限 + 慢重返。prefix /api/church-integration(/api/church 归 church.py)。email 标识用户。

CREATE TABLE IF NOT EXISTS church_profiles (
    id            VARCHAR(64)  PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    description   TEXT         DEFAULT '',
    denomination  VARCHAR(120) DEFAULT '',
    location_text VARCHAR(200) DEFAULT '',
    created_by_email VARCHAR(255) DEFAULT '',
    public        BOOLEAN      DEFAULT FALSE,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_church_connections (
    id                    VARCHAR(64)  PRIMARY KEY,
    email                 VARCHAR(255) NOT NULL,
    church_profile_id     VARCHAR(64)  DEFAULT '',
    connection_status     VARCHAR(20)  DEFAULT 'not_connected', -- not_connected/exploring/visiting/regular_attender/member/serving_member/leader/paused/left
    baptism_status        VARCHAR(16)  DEFAULT 'unknown',
    membership_status     VARCHAR(16)  DEFAULT 'unknown',
    small_group_status    VARCHAR(16)  DEFAULT 'unknown',
    pastoral_contact_status VARCHAR(16) DEFAULT 'unknown',
    notes                 TEXT         DEFAULT '',
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_church_conn_email ON user_church_connections (email, created_at DESC);

CREATE TABLE IF NOT EXISTS church_life_rhythms (
    id           VARCHAR(64)  PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    rhythm_type  VARCHAR(24)  DEFAULT 'worship',
    title        VARCHAR(160) NOT NULL,
    description  TEXT         DEFAULT '',
    frequency_type VARCHAR(12) DEFAULT 'weekly',
    next_due_at  TIMESTAMP,
    status       VARCHAR(12)  DEFAULT 'active',
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_church_rhythms_email ON church_life_rhythms (email, status);

CREATE TABLE IF NOT EXISTS church_life_checkins (
    id           VARCHAR(64)  PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    rhythm_id    VARCHAR(64)  DEFAULT '',
    checkin_date DATE         DEFAULT CURRENT_DATE,
    checkin_type VARCHAR(16)  DEFAULT 'worship',
    attended     BOOLEAN,
    reflection   TEXT         DEFAULT '',
    next_step    TEXT         DEFAULT '',
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_church_checkins_email ON church_life_checkins (email, checkin_date DESC);

CREATE TABLE IF NOT EXISTS church_reentry_plans (
    id                  VARCHAR(64)  PRIMARY KEY,
    email               VARCHAR(255) NOT NULL,
    reason_for_reentry  VARCHAR(24)  DEFAULT 'returning_after_absence',
    safety_concerns     JSONB        DEFAULT '[]'::jsonb,
    desired_church_traits JSONB      DEFAULT '[]'::jsonb,
    boundaries_needed   JSONB        DEFAULT '[]'::jsonb,
    first_steps         JSONB        DEFAULT '[]'::jsonb,
    support_person_needed BOOLEAN    DEFAULT FALSE,
    status              VARCHAR(12)  DEFAULT 'active',
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_church_reentry_email ON church_reentry_plans (email, status);
