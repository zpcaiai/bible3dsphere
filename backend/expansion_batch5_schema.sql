-- 属灵星球 · 扩充第四辑（13 表）· 忿怒/孤单/完美主义/嫉妒/耗竭/安慰/浪子/acedia/良心/主再来/慢性受苦/家庭门训/年老
CREATE TABLE IF NOT EXISTS anger_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_anger_email_time ON anger_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS loneliness_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_loneliness_email_time ON loneliness_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS perfectionism_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_perfectionism_email_time ON perfectionism_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS envy_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_envy_email_time ON envy_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS burnout_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_burnout_email_time ON burnout_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS comfort_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comfort_email_time ON comfort_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS prodigal_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prodigal_email_time ON prodigal_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS acedia_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_acedia_email_time ON acedia_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS conscience_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conscience_email_time ON conscience_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS second_coming_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_second_coming_email_time ON second_coming_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS chronic_suffering_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chronic_suffering_email_time ON chronic_suffering_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS parenting_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_parenting_email_time ON parenting_entries (email, created_at DESC);
CREATE TABLE IF NOT EXISTS aging_entries (
    id TEXT PRIMARY KEY, email TEXT NOT NULL, input_text TEXT,
    crisis BOOLEAN DEFAULT FALSE, prayer TEXT, analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_aging_email_time ON aging_entries (email, created_at DESC);
