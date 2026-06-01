-- Migration 0022: 等候之路 — 从「等待戈多」到「等候上帝」
--                  Waiting Transformation Module
--
-- 帮助用户把「虚无、被动、焦虑、幻想式」的等待，转化为「有信、有望、有爱、
-- 有行动、有顺服」的等候。本模块不定罪、不贴标签，是反思 / 分辨 / 陪伴式功能。
--
-- 幂等：所有对象使用 IF NOT EXISTS。用户以 email 标识（沿用 users.email，
--       取代规格中的 user_id UUID，以与本项目既有鉴权模型一致）。

-- ---------------------------------------------------------------------------
-- 1. 等待案例 (waiting_cases)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waiting_cases (
    id                       VARCHAR(64)  PRIMARY KEY,             -- uuid (应用层生成)
    email                    VARCHAR(255) NOT NULL,

    waiting_for              TEXT         NOT NULL,                -- 我在等什么
    waiting_description      TEXT         DEFAULT '',              -- 具体情况
    waiting_type             VARCHAR(20)  DEFAULT 'unknown',       -- godot_waiting|god_waiting|mixed|unknown

    -- 用户自评原始输入 (0–10)
    anxiety_level            REAL DEFAULT 0,
    hope_level               REAL DEFAULT 0,
    passivity_level          REAL DEFAULT 0,
    fantasy_level            REAL DEFAULT 0,
    trust_level              REAL DEFAULT 0,
    obedience_readiness      REAL DEFAULT 0,
    action_clarity           REAL DEFAULT 0,

    -- 分析得分 (0–1)
    idolatry_risk            REAL DEFAULT 0,
    emotional_dependency     REAL DEFAULT 0,
    responsibility_alignment REAL DEFAULT 0,

    analysis_json            JSONB DEFAULT '{}'::jsonb,            -- 完整分析结果留底
    guidance_text            TEXT  DEFAULT '',

    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_waiting_cases_email_created
    ON waiting_cases (email, created_at DESC);

-- ---------------------------------------------------------------------------
-- 2. 七天操练 (waiting_practices)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waiting_practices (
    id                VARCHAR(64)  PRIMARY KEY,
    waiting_case_id   VARCHAR(64)  NOT NULL REFERENCES waiting_cases(id) ON DELETE CASCADE,

    day_index         INTEGER      NOT NULL,                       -- 1..7
    practice_title    TEXT         DEFAULT '',
    practice_content  TEXT         DEFAULT '',
    reflection_prompt TEXT         DEFAULT '',
    completed         BOOLEAN      DEFAULT FALSE,
    user_reflection   TEXT         DEFAULT '',

    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_waiting_practices_case
    ON waiting_practices (waiting_case_id, day_index);

-- ---------------------------------------------------------------------------
-- 3. 等候复盘 (waiting_reflections)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waiting_reflections (
    id                VARCHAR(64)  PRIMARY KEY,
    waiting_case_id   VARCHAR(64)  NOT NULL REFERENCES waiting_cases(id) ON DELETE CASCADE,
    email             VARCHAR(255) NOT NULL,

    reflection_text   TEXT  DEFAULT '',
    anxiety_level     REAL  DEFAULT 0,
    hope_level        REAL  DEFAULT 0,
    trust_level       REAL  DEFAULT 0,
    leaning           VARCHAR(20) DEFAULT '',                      -- godot|god|mixed (用户主观自评)
    action_taken      TEXT  DEFAULT '',

    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_waiting_reflections_case_created
    ON waiting_reflections (waiting_case_id, created_at DESC);
