-- 0091_worldview_governance.sql
-- Worldview Formation OS — 群体协作与治理：守护人 / 告警 / Agent 事件
-- 幂等；email 为用户键。community_guardians 为 worldview-OS 的规范守护人登记表，
-- 可日后从既有 guardian_profiles + crisis_guardian_contacts 回填统一。
-- agent_runs / review_logs / community_feedback 已存在（迁移 0037 / 0069），此处不重建。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 守护人 / 小组长 / 牧者 / 家人 ----------------------------------------------
CREATE TABLE IF NOT EXISTS community_guardians (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                    TEXT NOT NULL,            -- 被守护者
    display_name             TEXT NOT NULL,
    role                     TEXT NOT NULL,            -- family/friend/pastor/small_group_leader/mentor/counselor/doctor/peer_companion/other
    contact_email            TEXT,
    contact_phone            TEXT,
    can_receive_crisis_alert BOOLEAN DEFAULT FALSE,
    can_receive_growth_summary BOOLEAN DEFAULT FALSE,
    consent_confirmed        BOOLEAN DEFAULT FALSE,
    priority_order           INT DEFAULT 1,
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_community_guardians_email ON community_guardians(email);

-- 危机 / 重要牧养告警 ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS guardian_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL,
    guardian_id     UUID,
    alert_type      TEXT NOT NULL,                     -- crisis/growth/check_in
    risk_level      TEXT DEFAULT 'yellow',             -- green/yellow/orange/red
    message         TEXT NOT NULL,
    status          TEXT DEFAULT 'drafted',            -- drafted/sent/acknowledged
    sent_at         TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_guardian_alerts_email_status ON guardian_alerts(email, status);

-- Agent 编排事件（跨 Agent 流转 / 异步处理）----------------------------------
CREATE TABLE IF NOT EXISTS agent_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT,
    event_type    TEXT NOT NULL,
    source_agent  TEXT,
    target_agent  TEXT,
    payload       JSONB DEFAULT '{}',
    status        TEXT DEFAULT 'pending',              -- pending/processed/failed
    scheduled_at  TIMESTAMPTZ,
    processed_at  TIMESTAMPTZ,
    retry_count   INT DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_events_email_status ON agent_events(email, status);
CREATE INDEX IF NOT EXISTS idx_agent_events_scheduled ON agent_events(scheduled_at);
