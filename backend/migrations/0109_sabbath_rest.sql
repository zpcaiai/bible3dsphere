-- Migration 0109: 安息日与休息操练 Sabbath & Rest（B4 Skill 15）
-- 不只是放一天假，而是重新安放敬拜、信靠、身体、时间与欲望。抵抗效率偶像。
-- 不强制周日、不使安息变律法、不羞辱不稳定作息者；burnout 时减负。email 标识用户。

CREATE TABLE IF NOT EXISTS sabbath_plans (
    id                    VARCHAR(64)  PRIMARY KEY,
    email                 VARCHAR(255) NOT NULL,
    title                 VARCHAR(120) DEFAULT '我的安息',
    status                VARCHAR(12)  DEFAULT 'active',
    sabbath_day           VARCHAR(12)  DEFAULT 'sunday',
    start_time            TIME,
    end_time              TIME,
    worship_plan          TEXT         DEFAULT '',
    rest_practices        JSONB        DEFAULT '[]'::jsonb,
    delight_practices     JSONB        DEFAULT '[]'::jsonb,
    technology_boundaries JSONB        DEFAULT '[]'::jsonb,
    work_boundaries       JSONB        DEFAULT '[]'::jsonb,
    preparation_tasks     JSONB        DEFAULT '[]'::jsonb,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sabbath_plans_email ON sabbath_plans (email, status);

CREATE TABLE IF NOT EXISTS sabbath_sessions (
    id                       VARCHAR(64)  PRIMARY KEY,
    email                    VARCHAR(255) NOT NULL,
    sabbath_plan_id          VARCHAR(64)  DEFAULT '',
    sabbath_date             DATE         NOT NULL,
    started_at               TIMESTAMP,
    ended_at                 TIMESTAMP,
    status                   VARCHAR(12)  DEFAULT 'planned', -- planned/started/completed/disrupted/skipped
    worship_completed        BOOLEAN      DEFAULT FALSE,
    rest_completed           BOOLEAN      DEFAULT FALSE,
    delight_completed        BOOLEAN      DEFAULT FALSE,
    technology_boundary_kept BOOLEAN,
    work_boundary_kept       BOOLEAN,
    disruption_notes         TEXT         DEFAULT '',
    grace_noticed            TEXT         DEFAULT '',
    created_at               TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sabbath_sessions_email ON sabbath_sessions (email, sabbath_date DESC);

CREATE TABLE IF NOT EXISTS rest_audits (
    id                         VARCHAR(64)  PRIMARY KEY,
    email                      VARCHAR(255) NOT NULL,
    audit_date                 DATE         NOT NULL,
    sleep_quality_score        INT,
    physical_fatigue_score     INT,
    emotional_fatigue_score    INT,
    spiritual_dryness_score    INT,
    work_pressure_score        INT,
    technology_overload_score  INT,
    relational_depletion_score INT,
    main_rest_blockers         JSONB        DEFAULT '[]'::jsonb,
    idols_detected             JSONB        DEFAULT '[]'::jsonb,
    recommended_rest_response  TEXT         DEFAULT '',
    created_at                 TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rest_audits_email ON rest_audits (email, audit_date DESC);

CREATE TABLE IF NOT EXISTS rest_boundary_rules (
    id               VARCHAR(64)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    title            VARCHAR(120) NOT NULL,
    boundary_type    VARCHAR(16)  DEFAULT 'work',  -- work/technology/sleep/social/money/ministry/custom
    rule_text        TEXT         DEFAULT '',
    active            BOOLEAN     DEFAULT TRUE,
    exception_policy TEXT         DEFAULT '',
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rest_boundaries_email ON rest_boundary_rules (email, active);
