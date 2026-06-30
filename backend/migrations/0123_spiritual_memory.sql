-- Migration 0123: 属灵记忆库 Spiritual Memory Store（B10 记忆库）
-- 个人成长画像 + 记忆条目 + 同意规则。
-- 原则:记忆是仆人不是主人 — 用户拥有、可编辑、可删除自己的记忆;
--       敏感/危机条目默认不外泄、不喂给 AI 导师(由 memory_consent_rules 控制)。

CREATE TABLE IF NOT EXISTS spiritual_profiles (
    email           VARCHAR(255) PRIMARY KEY,
    current_season  VARCHAR(60)  DEFAULT '',
    primary_focus   VARCHAR(120) DEFAULT '',
    practice_style  JSONB        DEFAULT '{}'::jsonb,
    caution_flags   JSONB        DEFAULT '[]'::jsonb,
    summary_text    TEXT         DEFAULT '',
    updated_at      TIMESTAMPTZ  DEFAULT now()
);

CREATE TABLE IF NOT EXISTS spiritual_memory_items (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    memory_type   VARCHAR(40)  DEFAULT 'insight',    -- insight|pattern|milestone|struggle|prayer|preference
    title         VARCHAR(200) DEFAULT '',
    content       TEXT         NOT NULL,
    source_module VARCHAR(40)  DEFAULT 'manual',
    sensitivity   VARCHAR(20)  DEFAULT 'normal',      -- normal|sensitive|crisis
    importance    SMALLINT     DEFAULT 3,             -- 1..5
    active        BOOLEAN      DEFAULT TRUE,
    created_at    TIMESTAMPTZ  DEFAULT now(),
    updated_at    TIMESTAMPTZ  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_spiritual_memory_email ON spiritual_memory_items(email, active);
CREATE INDEX IF NOT EXISTS idx_spiritual_memory_type  ON spiritual_memory_items(email, memory_type);

CREATE TABLE IF NOT EXISTS memory_consent_rules (
    email             VARCHAR(255) PRIMARY KEY,
    allow_ai_tutor    BOOLEAN DEFAULT TRUE,
    allow_mentor      BOOLEAN DEFAULT FALSE,
    allow_group       BOOLEAN DEFAULT FALSE,
    exclude_sensitive BOOLEAN DEFAULT TRUE,
    updated_at        TIMESTAMPTZ DEFAULT now()
);
