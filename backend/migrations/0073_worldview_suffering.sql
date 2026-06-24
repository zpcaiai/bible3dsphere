-- 0073_worldview_suffering.sql
-- Worldview Formation OS — 苦难神学 / 危机评估 / 用户授权
-- 幂等；email 为用户键。crisis_risk_assessments 与既有 crisis_events 互补（前者按世界观评估粒度）。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 危机风险评估（苦难/世界观入口的前置安全评估；与 crisis_events 互补）------------
CREATE TABLE IF NOT EXISTS crisis_risk_assessments (
    id                                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                              TEXT NOT NULL,
    source_type                        TEXT NOT NULL,
    source_id                          UUID,
    risk_level                         TEXT NOT NULL DEFAULT 'none',  -- none/low/medium/high/imminent
    markers                            JSONB DEFAULT '[]',
    evidence_summary                   TEXT,
    requires_immediate_safety_response BOOLEAN DEFAULT FALSE,
    should_avoid_theological_analysis  BOOLEAN DEFAULT FALSE,
    recommended_response_mode          TEXT,
    safety_notes                       JSONB DEFAULT '[]',
    recommended_next_steps             JSONB DEFAULT '[]',
    created_at                         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_crisis_risk_email_level ON crisis_risk_assessments(email, risk_level);

-- 苦难神学案例 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suffering_cases (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                     TEXT NOT NULL,
    source_type               TEXT NOT NULL,
    source_id                 UUID,
    suffering_text            TEXT NOT NULL,
    life_area                 TEXT DEFAULT 'suffering',
    suffering_type            TEXT,
    grief_type                TEXT,
    intensity                 INT CHECK (intensity BETWEEN 1 AND 10),
    theological_hypotheses    JSONB DEFAULT '[]',
    recommended_bible_persons JSONB DEFAULT '[]',
    recommended_scripture_refs JSONB DEFAULT '[]',
    lament_prayer             TEXT,
    hope_statement            TEXT,
    pastoral_response         TEXT,
    should_create_formation_plan BOOLEAN DEFAULT FALSE,
    should_link_crisis_system    BOOLEAN DEFAULT FALSE,
    created_at                TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_suffering_cases_email ON suffering_cases(email);

-- 用户授权（危机联动 / 牧者协作 / 长期记忆 / 数据分析）------------------------
CREATE TABLE IF NOT EXISTS user_consents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL,
    consent_key     TEXT NOT NULL,
    consent_scope   TEXT NOT NULL,
    enabled         BOOLEAN DEFAULT FALSE,
    consent_version TEXT,
    granted_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(email, consent_key)
);
CREATE INDEX IF NOT EXISTS idx_user_consents_email ON user_consents(email);
