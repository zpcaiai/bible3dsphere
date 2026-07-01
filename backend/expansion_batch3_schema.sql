-- 属灵星球 · 扩充第二辑（次要新大陆 5 表）
CREATE TABLE IF NOT EXISTS hope_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hope_email_time ON hope_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS prayer_school_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prayer_school_email_time ON prayer_school_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS contemplation_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_contemplation_email_time ON contemplation_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS incarnation_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incarnation_email_time ON incarnation_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS wisdom_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wisdom_email_time ON wisdom_entries (email, created_at DESC);
