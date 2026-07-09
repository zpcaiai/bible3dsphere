-- 0146_attention_module.sql — Attention Stewardship / 守心
--
-- This app's authenticated personal tables are primarily email-keyed TEXT
-- columns, so user_id is TEXT here instead of a UUID FK. API handlers fill it
-- from the server session, never from the client.

CREATE TABLE IF NOT EXISTS attention_daily_covenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    covenant_date DATE NOT NULL,

    primary_offering TEXT NOT NULL,
    mission_focus TEXT,
    worship_focus TEXT,
    relationship_focus TEXT,
    restoration_focus TEXT,

    main_risk TEXT,
    risk_pulls TEXT[] NOT NULL DEFAULT '{}',
    digital_boundary TEXT,
    time_boundary TEXT,
    spiritual_boundary TEXT,

    scripture_reference TEXT,
    scripture_text TEXT,
    prayer TEXT,

    status TEXT NOT NULL DEFAULT 'active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, covenant_date)
);

CREATE TABLE IF NOT EXISTS attention_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    entry_date DATE NOT NULL,
    category TEXT NOT NULL,
    activity_name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),

    attention_state TEXT,
    pulls TEXT[] NOT NULL DEFAULT '{}',

    note TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attention_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    review_date DATE NOT NULL,

    biggest_capture TEXT,
    biggest_grace TEXT,
    repentance_point TEXT,
    tomorrow_boundary TEXT,
    prayer TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, review_date)
);

CREATE TABLE IF NOT EXISTS attention_focus_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    planned_minutes INTEGER NOT NULL,
    actual_minutes INTEGER,

    focus_type TEXT NOT NULL,
    intention TEXT,
    opening_prayer TEXT,
    closing_reflection TEXT,

    interrupted BOOLEAN NOT NULL DEFAULT false,
    interruption_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attention_weekly_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    worship_minutes INTEGER NOT NULL DEFAULT 0,
    mission_minutes INTEGER NOT NULL DEFAULT 0,
    relationship_minutes INTEGER NOT NULL DEFAULT 0,
    restoration_minutes INTEGER NOT NULL DEFAULT 0,
    captured_minutes INTEGER NOT NULL DEFAULT 0,

    summary TEXT,
    main_pattern TEXT,
    recommended_practice TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, week_start, week_end)
);

CREATE OR REPLACE FUNCTION set_attention_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_attention_daily_covenants_updated_at ON attention_daily_covenants;
CREATE TRIGGER trg_attention_daily_covenants_updated_at
BEFORE UPDATE ON attention_daily_covenants
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_entries_updated_at ON attention_entries;
CREATE TRIGGER trg_attention_entries_updated_at
BEFORE UPDATE ON attention_entries
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_reviews_updated_at ON attention_reviews;
CREATE TRIGGER trg_attention_reviews_updated_at
BEFORE UPDATE ON attention_reviews
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

CREATE INDEX IF NOT EXISTS idx_attention_daily_covenants_user_date
ON attention_daily_covenants(user_id, covenant_date DESC);

CREATE INDEX IF NOT EXISTS idx_attention_entries_user_date
ON attention_entries(user_id, entry_date DESC);

CREATE INDEX IF NOT EXISTS idx_attention_reviews_user_date
ON attention_reviews(user_id, review_date DESC);

CREATE INDEX IF NOT EXISTS idx_attention_focus_sessions_user_started
ON attention_focus_sessions(user_id, started_at DESC);
