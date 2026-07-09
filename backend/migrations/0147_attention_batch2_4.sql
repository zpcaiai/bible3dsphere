-- 0147_attention_batch2_4.sql — Attention Stewardship Batch 2-4
-- Extends the email-keyed attention tables created in 0146. These tables store
-- only summaries/results needed for the product surfaces, not raw prompts.

CREATE UNIQUE INDEX IF NOT EXISTS uniq_attention_active_focus_session
ON attention_focus_sessions(user_id)
WHERE ended_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_attention_focus_sessions_user_active
ON attention_focus_sessions(user_id, started_at DESC)
WHERE ended_at IS NULL;

CREATE TABLE IF NOT EXISTS attention_ai_diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    diagnosis_date DATE NOT NULL,
    diagnosis_type TEXT NOT NULL DEFAULT 'daily',

    source_range_start DATE,
    source_range_end DATE,

    input_summary JSONB,
    result JSONB NOT NULL,

    provider TEXT,
    model_name TEXT,
    generated_by TEXT NOT NULL DEFAULT 'fallback',

    safety_level TEXT NOT NULL DEFAULT 'normal',
    saved_by_user BOOLEAN NOT NULL DEFAULT false,

    user_feedback TEXT,
    user_rating INTEGER CHECK (user_rating IS NULL OR user_rating BETWEEN 1 AND 5),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_ai_diagnoses_user_date
ON attention_ai_diagnoses(user_id, diagnosis_date DESC);

CREATE INDEX IF NOT EXISTS idx_attention_ai_diagnoses_user_type_date
ON attention_ai_diagnoses(user_id, diagnosis_type, diagnosis_date DESC);

CREATE TABLE IF NOT EXISTS attention_warfare_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    pattern_key TEXT NOT NULL,
    title TEXT NOT NULL,

    description TEXT,
    primary_pulls TEXT[] DEFAULT '{}',

    trigger_situations TEXT[] DEFAULT '{}',
    vulnerable_times TEXT[] DEFAULT '{}',
    common_behaviors TEXT[] DEFAULT '{}',

    possible_root TEXT,
    gospel_truth TEXT,

    scripture_reference TEXT,
    scripture_text TEXT,

    digital_boundary TEXT,
    time_boundary TEXT,
    spiritual_boundary TEXT,
    replacement_practice TEXT,
    escape_plan TEXT,
    accountability_prompt TEXT,

    status TEXT NOT NULL DEFAULT 'active',

    source_type TEXT,
    source_diagnosis_id UUID NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_warfare_plans_user_status
ON attention_warfare_plans(user_id, status);

CREATE INDEX IF NOT EXISTS idx_attention_warfare_plans_user_pattern
ON attention_warfare_plans(user_id, pattern_key);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_attention_warfare_plan_source_diagnosis
ON attention_warfare_plans(user_id, source_diagnosis_id)
WHERE source_diagnosis_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS attention_warfare_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    plan_id UUID NOT NULL REFERENCES attention_warfare_plans(id) ON DELETE CASCADE,

    checkin_date DATE NOT NULL,

    status TEXT NOT NULL,
    noticed BOOLEAN DEFAULT false,
    resisted BOOLEAN DEFAULT false,
    escaped BOOLEAN DEFAULT false,
    returned_to_god BOOLEAN DEFAULT false,

    trigger_observed TEXT,
    boundary_used TEXT,
    replacement_used TEXT,
    grace_noticed TEXT,
    tomorrow_adjustment TEXT,
    prayer TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, plan_id, checkin_date)
);

CREATE INDEX IF NOT EXISTS idx_attention_warfare_checkins_user_date
ON attention_warfare_checkins(user_id, checkin_date DESC);

CREATE INDEX IF NOT EXISTS idx_attention_warfare_checkins_plan_date
ON attention_warfare_checkins(plan_id, checkin_date DESC);

DROP TRIGGER IF EXISTS trg_attention_ai_diagnoses_updated_at ON attention_ai_diagnoses;
CREATE TRIGGER trg_attention_ai_diagnoses_updated_at
BEFORE UPDATE ON attention_ai_diagnoses
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_warfare_plans_updated_at ON attention_warfare_plans;
CREATE TRIGGER trg_attention_warfare_plans_updated_at
BEFORE UPDATE ON attention_warfare_plans
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_warfare_checkins_updated_at ON attention_warfare_checkins;
CREATE TRIGGER trg_attention_warfare_checkins_updated_at
BEFORE UPDATE ON attention_warfare_checkins
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();
