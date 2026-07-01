-- ============================================================================
-- Church Health OS — 健康教会九标志 数据表
-- ----------------------------------------------------------------------------
-- 说明：这些表由 church_health_engine.ensure_tables() 在首个请求时懒建（与本仓库
-- 其它模块一致），本文件仅作为可读的 schema 参考 / 手动初始化脚本。
-- 归属：按登录用户 email。隐私优先：悔改/福音评估默认仅本人可见。
-- ============================================================================

-- 本地教会委身档案（每用户一行）
CREATE TABLE IF NOT EXISTS ch_membership (
    email                          TEXT PRIMARY KEY,
    church_name                    TEXT,
    church_id                      TEXT,
    membership_status              TEXT NOT NULL DEFAULT 'none',   -- none/visitor/regular_attender/member_candidate/member/inactive/transferred
    baptism_status                 TEXT NOT NULL DEFAULT 'unknown',-- unknown/unbaptized/scheduled/baptized
    joined_at                      DATE,
    small_group_name               TEXT,
    worship_attendance             BOOLEAN NOT NULL DEFAULT FALSE,
    small_group_participation      BOOLEAN NOT NULL DEFAULT FALSE,
    pastoral_connection            BOOLEAN NOT NULL DEFAULT FALSE,
    service_roles                  JSONB   NOT NULL DEFAULT '[]'::jsonb,
    one_another_notes              TEXT,
    consent_to_share_with_leader   BOOLEAN NOT NULL DEFAULT FALSE,
    consent_to_anonymous_aggregate BOOLEAN NOT NULL DEFAULT TRUE,
    notes                          TEXT,
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 主日讲道记录与回应（释经讲道标志）
CREATE TABLE IF NOT EXISTS ch_sermon_records (
    id                SERIAL PRIMARY KEY,
    email             TEXT NOT NULL,
    church_name       TEXT,
    preacher_name     TEXT,
    sermon_title      TEXT,
    scripture_ref     TEXT NOT NULL,
    sermon_date       DATE,
    raw_notes         TEXT,
    main_point        TEXT,
    gospel_connection TEXT,
    repentance_prompt TEXT,
    faith_prompt      TEXT,
    obedience_action  TEXT,
    community_action  TEXT,
    visibility        TEXT NOT NULL DEFAULT 'private',  -- private/leader/group
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_sermon_email ON ch_sermon_records(email, created_at DESC);

-- 福音清晰度评估（福音标志；强隐私，仅本人）
CREATE TABLE IF NOT EXISTS ch_gospel_assessments (
    id                   SERIAL PRIMARY KEY,
    email                TEXT NOT NULL,
    source_type          TEXT NOT NULL DEFAULT 'user_reflection',
    source_text          TEXT,
    god_score            INT NOT NULL DEFAULT 0,   -- 0..5
    sin_score            INT NOT NULL DEFAULT 0,
    christ_score         INT NOT NULL DEFAULT 0,
    response_score       INT NOT NULL DEFAULT 0,
    detected_distortions JSONB NOT NULL DEFAULT '[]'::jsonb, -- 道德主义/成功神学/治疗主义/律法主义/廉价恩典/个人主义
    gentle_reframe       TEXT,
    next_teaching        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_gospel_email ON ch_gospel_assessments(email, created_at DESC);

-- 悔改与恢复记录（教会纪律标志；极高隐私，默认仅本人；不自动通知领袖）
CREATE TABLE IF NOT EXISTS ch_repentance_patterns (
    id                  SERIAL PRIMARY KEY,
    email               TEXT NOT NULL,
    sin_pattern         TEXT NOT NULL,
    trigger_context     TEXT,
    confession_notes    TEXT,
    repentance_steps    JSONB NOT NULL DEFAULT '[]'::jsonb,
    accountability_plan TEXT,
    repentance_status   TEXT NOT NULL DEFAULT 'struggling', -- struggling/repenting/restoring/stable
    risk_level          TEXT NOT NULL DEFAULT 'low',        -- low/medium/high/crisis
    leader_visibility   TEXT NOT NULL DEFAULT 'private',    -- private/leader
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_repent_email ON ch_repentance_patterns(email, created_at DESC);

-- 门训关系（门徒造就标志）
CREATE TABLE IF NOT EXISTS ch_discipleship (
    id              SERIAL PRIMARY KEY,
    email           TEXT NOT NULL,     -- 记录创建者（本人是 mentor 或 mentee 之一）
    counterpart     TEXT,              -- 对方（昵称或 email）
    relation_type   TEXT NOT NULL DEFAULT 'peer',  -- being_discipled/discipling/peer
    goals           JSONB NOT NULL DEFAULT '[]'::jsonb,
    meeting_rhythm  TEXT,
    last_meeting_at TIMESTAMPTZ,
    next_meeting_at TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_disciple_email ON ch_discipleship(email, created_at DESC);

-- 九标志个人成长快照（每次 compute 落一批，mark_code 一行）
CREATE TABLE IF NOT EXISTS ch_mark_snapshots (
    id              SERIAL PRIMARY KEY,
    email           TEXT NOT NULL,
    batch_id        TEXT NOT NULL,
    mark_code       TEXT NOT NULL,
    score           INT NOT NULL DEFAULT 0,
    band            TEXT,               -- healthy/growing/attention/seedling
    evidence        JSONB NOT NULL DEFAULT '{}'::jsonb,
    risks           JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall_score   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_snap_email ON ch_mark_snapshots(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ch_snap_batch ON ch_mark_snapshots(batch_id);

-- 牧养关怀信号（教会带领标志；本人可读；leader 仅在授权/安全策略下可读授权信号）
CREATE TABLE IF NOT EXISTS ch_care_signals (
    id                 SERIAL PRIMARY KEY,
    email              TEXT NOT NULL,
    church_id          TEXT,
    signal_type        TEXT NOT NULL,
    severity           TEXT NOT NULL DEFAULT 'low',
    summary            TEXT,
    recommended_action TEXT,
    consent_share      BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_care_email ON ch_care_signals(email, created_at DESC);
