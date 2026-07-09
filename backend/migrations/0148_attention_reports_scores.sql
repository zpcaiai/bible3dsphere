-- 0148_attention_reports_scores.sql — Attention Stewardship Batch 5
-- Adds rhythm scores, weekly reports, and growth-curve support. Tables remain
-- email-keyed TEXT to match the existing attention module.

CREATE TABLE IF NOT EXISTS attention_daily_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    score_date DATE NOT NULL,

    score INTEGER CHECK (score IS NULL OR score BETWEEN 0 AND 100),
    score_label TEXT,
    data_completeness INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL DEFAULT 'low',

    component_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    input_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    insights JSONB NOT NULL DEFAULT '{}'::jsonb,

    generated_by TEXT NOT NULL DEFAULT 'rules',
    version TEXT NOT NULL DEFAULT 'v1',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, score_date)
);

CREATE INDEX IF NOT EXISTS idx_attention_daily_scores_user_date
ON attention_daily_scores(user_id, score_date DESC);

ALTER TABLE attention_weekly_reports
ADD COLUMN IF NOT EXISTS score_average INTEGER,
ADD COLUMN IF NOT EXISTS score_label TEXT,
ADD COLUMN IF NOT EXISTS score_trend TEXT,
ADD COLUMN IF NOT EXISTS data_completeness INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS daily_scores JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS category_minutes JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS category_percentages JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS focus_summary JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS covenant_summary JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS review_summary JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS warfare_summary JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS top_pulls JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS growth_signals JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS report_sections JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS next_week_practice TEXT,
ADD COLUMN IF NOT EXISTS prayer TEXT,
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'generated',
ADD COLUMN IF NOT EXISTS version TEXT NOT NULL DEFAULT 'v1',
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_attention_weekly_reports_user_week
ON attention_weekly_reports(user_id, week_start DESC);

CREATE INDEX IF NOT EXISTS idx_attention_weekly_reports_user_status
ON attention_weekly_reports(user_id, status);

DROP TRIGGER IF EXISTS trg_attention_daily_scores_updated_at ON attention_daily_scores;
CREATE TRIGGER trg_attention_daily_scores_updated_at
BEFORE UPDATE ON attention_daily_scores
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_weekly_reports_updated_at ON attention_weekly_reports;
CREATE TRIGGER trg_attention_weekly_reports_updated_at
BEFORE UPDATE ON attention_weekly_reports
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();
