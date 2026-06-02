-- Migration 0035: 代祷tab — 门徒塑造引擎 (Disciple Formation Engine / DFOS v1.0)
-- 把"门徒倍增"愿景落成可计算闭环：属灵数字孪生 + 状态机 + 11 引擎评估 + 倍增网络。
-- 适配本项目栈：用 Postgres JSONB(twin) 近似 Neo4j 图谱；用户以 email 标识（沿用 users.email）。
-- 幂等：所有对象使用 IF NOT EXISTS。

-- ---------------------------------------------------------------------------
-- 1. 属灵画像 / 数字孪生（每用户一行，聚合根 UserSpiritualProfile）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disciple_profiles (
    email                  VARCHAR(255) PRIMARY KEY,
    spiritual_state        VARCHAR(40)  NOT NULL DEFAULT 'SEEKER',
    next_state             VARCHAR(40)  DEFAULT '',
    christlikeness_index   NUMERIC(5,2) DEFAULT 0,
    -- 11 维塑造分（0~100）
    faith_score            NUMERIC(5,2) DEFAULT 50,
    hope_score             NUMERIC(5,2) DEFAULT 50,
    love_score             NUMERIC(5,2) DEFAULT 50,
    truth_score            NUMERIC(5,2) DEFAULT 50,
    prayer_score           NUMERIC(5,2) DEFAULT 50,
    obedience_score        NUMERIC(5,2) DEFAULT 50,
    character_score        NUMERIC(5,2) DEFAULT 50,
    calling_score          NUMERIC(5,2) DEFAULT 50,
    service_score          NUMERIC(5,2) DEFAULT 50,
    mission_score          NUMERIC(5,2) DEFAULT 50,
    multiplication_score   NUMERIC(5,2) DEFAULT 50,
    top_idol               VARCHAR(40)  DEFAULT '',
    growth_edge            VARCHAR(40)  DEFAULT 'faith',
    -- 完整孪生（dims/idols/character/engines 最新快照），近似图谱上下文
    twin                   JSONB        DEFAULT '{}'::jsonb,
    assessment_count       INTEGER      DEFAULT 0,
    created_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 2. 评估历史（每次反思 → 一份完整门徒塑造病历，含 11 引擎与导师七段）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disciple_assessments (
    id                     BIGSERIAL PRIMARY KEY,
    email                  VARCHAR(255) NOT NULL,
    journal                TEXT DEFAULT '',
    scripture              TEXT DEFAULT '',
    prayer                 TEXT DEFAULT '',
    spiritual_state        VARCHAR(40) DEFAULT 'SEEKER',
    christlikeness_index   NUMERIC(5,2) DEFAULT 0,
    growth_edge            VARCHAR(40) DEFAULT '',
    top_idol               VARCHAR(40) DEFAULT '',
    next_step              TEXT DEFAULT '',
    source                 VARCHAR(20) DEFAULT 'heuristic',   -- heuristic | ai
    report                 JSONB NOT NULL DEFAULT '{}'::jsonb, -- 完整 assess() 输出
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_disciple_assess_email
    ON disciple_assessments(email, created_at DESC);

-- ---------------------------------------------------------------------------
-- 3. 门徒关系网络（近似 Neo4j 的 DISCIPLES/MENTORS 边，支撑倍增链 + DMI）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS disciple_relationships (
    id                BIGSERIAL PRIMARY KEY,
    mentor_email      VARCHAR(255) NOT NULL,             -- 带领者
    disciple_email    VARCHAR(255) DEFAULT '',           -- 被带领者(注册用户)
    disciple_name     VARCHAR(120) DEFAULT '',           -- 或仅记名字(未必是注册用户)
    relationship_type VARCHAR(20) NOT NULL DEFAULT 'DISCIPLER', -- MENTOR|DISCIPLER|SPIRITUAL_PARENT|PEER
    status            VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',     -- ACTIVE|PAUSED|ENDED
    growth_goals      JSONB DEFAULT '[]'::jsonb,
    started_at        DATE DEFAULT CURRENT_DATE,
    ended_at          DATE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_disciple_rel_mentor
    ON disciple_relationships(mentor_email) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_disciple_rel_disciple
    ON disciple_relationships(disciple_email) WHERE status = 'ACTIVE';
