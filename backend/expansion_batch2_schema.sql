-- 属灵星球 · 内容与神学扩充第二辑（2026-07）· 8 个新引擎的持久化表
-- 得救确据 / 饶恕 / 团契 / 安息节奏 / 敬畏神 / 感恩(eucharisteo) / 成圣 / 爱邻舍
-- 统一结构；均为 best-effort 写入，缺表不影响 analyze 返回。

CREATE TABLE IF NOT EXISTS assurance_entries (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE,
    prayer TEXT,
    analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_assurance_email_time ON assurance_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS forgiveness_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_forgiveness_email_time ON forgiveness_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS fellowship_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fellowship_email_time ON fellowship_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS rule_of_life_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rule_of_life_email_time ON rule_of_life_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS fear_of_god_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fear_of_god_email_time ON fear_of_god_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS eucharisteo_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_eucharisteo_email_time ON eucharisteo_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS holiness_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_holiness_email_time ON holiness_entries (email, created_at DESC);

CREATE TABLE IF NOT EXISTS neighbor_love_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_neighbor_love_email_time ON neighbor_love_entries (email, created_at DESC);
