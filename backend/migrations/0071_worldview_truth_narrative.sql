-- 0071_worldview_truth_narrative.sql
-- Worldview Formation OS — 真理映射 / 扭曲信念 / 福音叙事重写
-- 幂等；email 为用户键。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 扭曲信念 --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS distorted_beliefs (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                  TEXT NOT NULL,
    belief_id              UUID,
    domain                 TEXT NOT NULL,
    distortion_type        TEXT,
    lie_statement          TEXT NOT NULL,
    idol_category          TEXT,
    severity               INT CHECK (severity BETWEEN 1 AND 10),
    emotional_fruit        JSONB DEFAULT '[]',
    behavioral_fruit       JSONB DEFAULT '[]',
    relational_fruit       JSONB DEFAULT '[]',
    spiritual_fruit        JSONB DEFAULT '[]',
    biblical_truth_summary TEXT,
    repentance_direction   TEXT,
    status                 TEXT DEFAULT 'distorted',
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_distorted_beliefs_email ON distorted_beliefs(email);
CREATE INDEX IF NOT EXISTS idx_distorted_beliefs_idol ON distorted_beliefs(idol_category);

-- 谎言 → 圣经真理映射（可作为知识库 / 缓存层；engine 内置确定性映射的持久化镜像）---
CREATE TABLE IF NOT EXISTS biblical_truth_maps (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain               TEXT NOT NULL,
    distortion_type      TEXT,
    idol_category        TEXT,
    lie_statement_pattern TEXT,
    biblical_truth       TEXT NOT NULL,
    gospel_reframe       TEXT,
    scripture_refs       JSONB DEFAULT '[]',
    doctrine_tags        JSONB DEFAULT '[]',
    bible_persons        JSONB DEFAULT '[]',
    pastoral_cautions    JSONB DEFAULT '[]',
    practice_suggestions JSONB DEFAULT '[]',
    is_active            BOOLEAN DEFAULT TRUE,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_truth_maps_domain ON biblical_truth_maps(domain);
CREATE INDEX IF NOT EXISTS idx_truth_maps_idol ON biblical_truth_maps(idol_category);

-- 生命叙事重写 ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS narrative_rewrites (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                    TEXT NOT NULL,
    old_narrative            TEXT NOT NULL,
    old_narrative_template   TEXT,
    core_fear                TEXT,
    hidden_idol              TEXT,
    core_lie                 TEXT,
    gospel_truth             TEXT NOT NULL,
    new_narrative            TEXT NOT NULL,
    scripture_refs           JSONB DEFAULT '[]',
    recommended_bible_persons JSONB DEFAULT '[]',
    practice_plan            JSONB DEFAULT '[]',
    reflection_questions     JSONB DEFAULT '[]',
    user_accepted            BOOLEAN,
    user_reflection          TEXT,
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_narrative_rewrites_email ON narrative_rewrites(email);
