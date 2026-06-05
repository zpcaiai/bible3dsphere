-- Migration 0044: 属灵守护者 / AI Companion Sprite (Spiritual Guardian)
-- 右下角常驻陪伴精灵：聊天、情绪/属灵打卡、祷告本、SOAP 灵修、
-- 长期记忆、行为模式、偶像信号、成长阶段。按 email 隔离用户。

-- Guardian 档案（每人一个精灵）
CREATE TABLE IF NOT EXISTS guardian_profiles (
    id                VARCHAR(64)  PRIMARY KEY,
    email             VARCHAR(255) NOT NULL UNIQUE,
    name              VARCHAR(64)  DEFAULT '守护者',
    form_stage        VARCHAR(16)  DEFAULT 'seed',   -- seed|sprout|lamp|guardian|pilgrim|messenger
    intimacy_level    INTEGER      DEFAULT 1,
    personality_style VARCHAR(32)  DEFAULT 'gentle',
    visual_skin       VARCHAR(32)  DEFAULT 'flame',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Guardian 实时状态
CREATE TABLE IF NOT EXISTS guardian_states (
    id                  VARCHAR(64)  PRIMARY KEY,
    email               VARCHAR(255) NOT NULL UNIQUE,
    current_mood        VARCHAR(24)  DEFAULT 'calm',
    spiritual_state     VARCHAR(24)  DEFAULT 'steady',  -- growing|steady|seeking|dry|struggling
    energy_level        INTEGER      DEFAULT 80,
    sprite_state        VARCHAR(24)  DEFAULT 'idle',    -- idle|listening|comforting|praying|celebrating|resting
    last_interaction_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 情绪事件（聊天分析 + 主动打卡）
CREATE TABLE IF NOT EXISTS guardian_emotion_events (
    id           VARCHAR(64)  PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    emotion_type VARCHAR(24)  NOT NULL,
    intensity    INTEGER      DEFAULT 5,        -- 1-10
    trigger      TEXT,
    note         TEXT,
    source       VARCHAR(16)  DEFAULT 'chat',   -- chat|checkin
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_emotion_email
    ON guardian_emotion_events (email, created_at DESC);

-- 属灵状态打卡（信/望/爱）
CREATE TABLE IF NOT EXISTS guardian_spiritual_checkins (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    faith_level     INTEGER DEFAULT 5,
    hope_level      INTEGER DEFAULT 5,
    love_level      INTEGER DEFAULT 5,
    spiritual_state VARCHAR(24) DEFAULT 'steady',
    note            TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_spiritual_email
    ON guardian_spiritual_checkins (email, created_at DESC);

-- 祷告记录（ACTS 分类，可标记应允）
CREATE TABLE IF NOT EXISTS guardian_prayer_entries (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    title       VARCHAR(120) DEFAULT '',
    content     TEXT NOT NULL,
    category    VARCHAR(24)  DEFAULT 'supplication', -- adoration|confession|thanksgiving|supplication|intercession
    status      VARCHAR(16)  DEFAULT 'ongoing',      -- ongoing|answered|archived
    answered_at TIMESTAMP,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_prayer_email
    ON guardian_prayer_entries (email, created_at DESC);

-- SOAP 灵修日志
CREATE TABLE IF NOT EXISTS guardian_devotion_entries (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    scripture   VARCHAR(255) DEFAULT '',
    observation TEXT,
    application TEXT,
    prayer      TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_devotion_email
    ON guardian_devotion_entries (email, created_at DESC);

-- 行为模式（温柔的镜子，非定论）
CREATE TABLE IF NOT EXISTS guardian_behavior_patterns (
    id               VARCHAR(64)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    pattern_type     VARCHAR(64)  NOT NULL,
    trigger          TEXT,
    typical_response TEXT,
    spiritual_root   TEXT,
    confidence       REAL DEFAULT 0.5,
    last_seen_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email, pattern_type)
);

-- 偶像信号（温和觉察：成就|金钱|关系|控制|舒适|认可|自我形象）
CREATE TABLE IF NOT EXISTS guardian_idol_signals (
    id         VARCHAR(64)  PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    idol_type  VARCHAR(24)  NOT NULL,
    signal     TEXT,
    intensity  INTEGER DEFAULT 3,   -- 1-5
    evidence   TEXT,
    suggestion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_idol_email
    ON guardian_idol_signals (email, created_at DESC);

-- 长期陪伴记忆（embedding 为 pgvector 预留，先存 JSONB）
CREATE TABLE IF NOT EXISTS guardian_memories (
    id          VARCHAR(64)  PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    memory_type VARCHAR(24)  DEFAULT 'event',  -- event|stressor|goal|prayer-item|relationship|preference
    content     TEXT NOT NULL,
    importance  INTEGER DEFAULT 3,             -- 1-5
    embedding   JSONB,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_memory_email
    ON guardian_memories (email, created_at DESC);

-- 对话消息
CREATE TABLE IF NOT EXISTS guardian_messages (
    id         VARCHAR(64)  PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    role       VARCHAR(12)  NOT NULL,            -- user|assistant
    content    TEXT NOT NULL,
    mode       VARCHAR(24)  DEFAULT 'companion', -- companion|comfort|prayer|devotion|reflection|idol-monitor|growth
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_guardian_messages_email
    ON guardian_messages (email, created_at DESC);
