-- 0078_suffering_care.sql
-- Advanced Batch · Module 6 — Suffering Theology & Crisis Linkage
-- Idempotent. Builds on suffering_cases (0073), crisis_events (crisis_schema.sql),
-- and care_signals (0077). Adds lament prayers, care plans, and the columns that
-- wire a suffering case to a crisis event.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Extend suffering_cases with the agent's structured fields + crisis link ----
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS case_type TEXT;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS risk_level TEXT DEFAULT 'low';
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS suffering_stage TEXT;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS theological_theme TEXT;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS lament_needed BOOLEAN DEFAULT FALSE;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS community_support_needed BOOLEAN DEFAULT FALSE;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS professional_help_recommended BOOLEAN DEFAULT FALSE;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS crisis_event_id TEXT;
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'open';
ALTER TABLE suffering_cases ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_suffering_cases_email_created ON suffering_cases(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_suffering_cases_risk ON suffering_cases(risk_level) WHERE status <> 'closed';

-- Lament prayers (a safe place to cry out; may be kept private) --------------
CREATE TABLE IF NOT EXISTS lament_prayers (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email            TEXT NOT NULL,
    suffering_case_id UUID REFERENCES suffering_cases(id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    raw_lament       TEXT NOT NULL,
    guided_prayer    TEXT,
    scripture_anchors JSONB DEFAULT '[]'::jsonb,
    share_level      TEXT DEFAULT 'private',         -- private|partner|group|pastor
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lament_prayers_email ON lament_prayers(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lament_prayers_case ON lament_prayers(suffering_case_id);

-- Care plans (scripture / prayer / community / professional path) ------------
CREATE TABLE IF NOT EXISTS suffering_care_plans (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email            TEXT NOT NULL,
    suffering_case_id UUID REFERENCES suffering_cases(id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    description      TEXT DEFAULT '',
    plan_type        TEXT NOT NULL DEFAULT 'lament', -- lament|trust|endurance|hope|presence|...
    scripture_path   JSONB DEFAULT '[]'::jsonb,
    prayer_path      JSONB DEFAULT '[]'::jsonb,
    community_actions JSONB DEFAULT '[]'::jsonb,
    professional_help_notes TEXT,
    duration_days    INTEGER DEFAULT 14,
    status           TEXT DEFAULT 'draft',           -- draft|active|completed|paused
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_suffering_care_plans_email ON suffering_care_plans(email, status);
CREATE INDEX IF NOT EXISTS idx_suffering_care_plans_case ON suffering_care_plans(suffering_case_id);
