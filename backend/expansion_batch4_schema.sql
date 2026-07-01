-- 属灵星球 · 扩充第三辑（10 表）· 圣灵/收纳/十架/怕人/护理/悔改/怀疑/慷慨/谦卑/爱慕神的话
CREATE TABLE IF NOT EXISTS holy_spirit_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_holy_spirit_email_time ON holy_spirit_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS adoption_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_adoption_email_time ON adoption_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS cross_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cross_email_time ON cross_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS fear_of_man_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fear_of_man_email_time ON fear_of_man_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS providence_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_providence_email_time ON providence_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS repentance_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_repentance_email_time ON repentance_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS doubt_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_doubt_email_time ON doubt_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS generosity_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_generosity_email_time ON generosity_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS humility_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_humility_email_time ON humility_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS word_delight_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_word_delight_email_time ON word_delight_entries (email, created_at DESC);
