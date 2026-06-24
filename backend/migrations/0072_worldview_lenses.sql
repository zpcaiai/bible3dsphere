-- 0072_worldview_lenses.sql
-- Worldview Formation OS — 护教学 / 文化分辨 / 职业使命 案例表
-- 幂等；email 为用户键（匿名提问可为空字符串）。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 护教学案例 ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apologetics_cases (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                    TEXT,
    topic                    TEXT NOT NULL,
    question                 TEXT NOT NULL,
    detected_presuppositions JSONB DEFAULT '[]',
    secular_framings         JSONB DEFAULT '[]',
    biblical_framing         TEXT,
    apologetics_response     TEXT,
    scripture_refs           JSONB DEFAULT '[]',
    doctrine_tags            JSONB DEFAULT '[]',
    recommended_resources    JSONB DEFAULT '[]',
    confidence               NUMERIC(5,2),
    pastoral_caution         TEXT,
    created_at               TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apologetics_cases_email ON apologetics_cases(email);
CREATE INDEX IF NOT EXISTS idx_apologetics_cases_topic ON apologetics_cases(topic);

-- 文化分辨案例 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cultural_discernment_cases (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT,
    cultural_topic      TEXT NOT NULL,
    user_input          TEXT NOT NULL,
    detected_spirits    JSONB DEFAULT '[]',
    cultural_liturgies  JSONB DEFAULT '[]',
    hidden_promises     JSONB DEFAULT '[]',
    hidden_demands      JSONB DEFAULT '[]',
    biblical_discernment TEXT,
    risks_for_user      JSONB DEFAULT '[]',
    counter_practices   JSONB DEFAULT '[]',
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cultural_cases_email ON cultural_discernment_cases(email);

-- 职业使命案例 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vocation_worldview_cases (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                  TEXT NOT NULL,
    vocation_context       TEXT NOT NULL,
    current_question       TEXT,
    work_view_detected     TEXT,
    calling_view_detected  TEXT,
    money_view_detected    TEXT,
    success_view_detected  TEXT,
    possible_idols         JSONB DEFAULT '[]',
    kingdom_opportunities  JSONB DEFAULT '[]',
    ethical_risks          JSONB DEFAULT '[]',
    biblical_vocation_frame TEXT,
    suggested_next_steps   JSONB DEFAULT '[]',
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vocation_cases_email ON vocation_worldview_cases(email);
